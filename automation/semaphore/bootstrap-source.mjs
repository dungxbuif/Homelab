import fs from 'node:fs/promises';

// Bootstrap only: never switches an existing provisioning template or repository.
const apply = process.argv.includes('--apply');
if (process.argv.slice(2).some(arg => arg !== '--apply')) throw new Error('Usage: node bootstrap-source.mjs [--apply]');
const base = 'https://semaphore.dungxbuif.com';
const source = JSON.parse(await fs.readFile('credentials/gitlab-semaphore-source.json', 'utf8'));
const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
const login = await fetch(base + '/api/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ auth: 'admin', password }), signal: AbortSignal.timeout(15000),
});
if (!login.ok) throw new Error(`Login HTTP ${login.status}`);
const cookie = login.headers.getSetCookie().map(value => value.split(';')[0]).join('; ');
async function api(route, body) {
  const response = await fetch(base + '/api/project/1' + route, {
    method: body ? 'POST' : 'GET',
    headers: { cookie, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(60000),
  });
  if (!response.ok) throw new Error(`Semaphore ${route}: HTTP ${response.status}`);
  return response.json();
}
const keyName = 'GitLab automation source (read only)';
const repoName = 'Homelab automation GitLab';
const matches = (items, name) => {
  const found = items.filter(item => item.name === name);
  if (found.length > 1) throw new Error(`Duplicate resource: ${name}`);
  return found[0];
};
let key = matches(await api('/keys'), keyName);
let repo = matches(await api('/repositories'), repoName);
if (!apply) {
  console.log(JSON.stringify({ mode: 'dry-run', key: key?.id ?? 'would-create', repository: repo?.id ?? 'would-create' }));
} else {
  if (!source.token || !source.username || source.scopes?.join(',') !== 'read_repository') {
    throw new Error('Expected repository-only deploy credential');
  }
  if (!key) key = await api('/keys', {
    name: keyName, type: 'login_password', project_id: 1,
    login_password: { login: source.username, password: source.token },
  });
  if (key.type !== 'login_password') throw new Error('Existing key type mismatch');
  const desired = {
    name: repoName, project_id: 1, ssh_key_id: key.id,
    git_url: 'https://gitlab.dungxbuif.com/dungxbuif/homelab-automation.git',
    git_branch: 'codex/automation-bootstrap',
  };
  if (!repo) repo = await api('/repositories', desired);
  for (const field of ['project_id', 'ssh_key_id', 'git_url', 'git_branch']) {
    if (repo[field] !== desired[field]) throw new Error(`Existing repository mismatch: ${field}`);
  }
  const branches = await api(`/repositories/${repo.id}/branches`);
  console.log(JSON.stringify({ key_id: key.id, repository_id: repo.id, branches, provisioning_template_changed: false }));
}
