import fs from 'node:fs/promises';

const apply = process.argv.includes('--apply');
if (process.argv.slice(2).some((arg) => arg !== '--apply')) {
  throw new Error('Usage: node bootstrap-backup-client-release.mjs [--apply]');
}

const base = 'https://semaphore.dungxbuif.com';
const project = '/api/project/1';
const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
const routeBootstrap = JSON.parse(await fs.readFile('credentials/pi-route-bootstrap.json', 'utf8'));

const login = await fetch(`${base}/api/auth/login`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({auth: 'admin', password}),
  signal: AbortSignal.timeout(15000),
});
if (!login.ok) throw new Error(`Login HTTP ${login.status}`);
const cookie = login.headers.getSetCookie().map((value) => value.split(';')[0]).join('; ');

async function api(path, options = {}) {
  const response = await fetch(base + project + path, {
    ...options,
    headers: {...(options.headers || {}), cookie, 'Content-Type': 'application/json'},
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`Semaphore ${path}: HTTP ${response.status}`);
  return response.status === 204 ? null : response.json();
}

function one(items, name) {
  const matches = items.filter((item) => item.name === name);
  if (matches.length > 1) throw new Error(`Duplicate resource: ${name}`);
  return matches[0];
}

const keyName = 'Pi5 backup client release (SSH)';
const repositoryName = 'Homelab automation release branch';
const inventoryName = 'Pi5 backup client release only';
const templateName = 'Release backup client (Pi5)';
const desiredBranch = 'codex/relayhub-source-foundation';

let key = one(await api('/keys'), keyName);
let repository = one(await api('/repositories'), repositoryName);
let inventory = one(await api('/inventory'), inventoryName);
let template = one(await api('/templates'), templateName);

if (!apply) {
  console.log(JSON.stringify({
    mode: 'dry-run',
    key: key?.id ?? 'create',
    repository: repository?.id ?? 'create',
    inventory: inventory?.id ?? 'create',
    template: template?.id ?? 'create',
    branch: desiredBranch,
    scope: 'pi5-only',
  }));
} else {
  if (!routeBootstrap.ansible_user) {
    throw new Error('Pi route bootstrap user is incomplete');
  }
  if (!key) {
    key = await api('/keys', {
      method: 'POST',
      body: JSON.stringify({
        name: keyName,
        type: 'ssh',
        project_id: 1,
        ssh: {
          login: routeBootstrap.ansible_user,
          private_key: await fs.readFile('credentials/semaphore-pi-backup-release', 'utf8'),
        },
      }),
    });
  }
  if (key.type !== 'ssh') throw new Error('Existing key type mismatch');

  const repositoryDesired = {
    name: repositoryName,
    project_id: 1,
    // Repository access uses the existing read-only GitLab source key, not the
    // target-host password key created above.
    ssh_key_id: 2,
    git_url: 'https://gitlab.dungxbuif.com/dungxbuif/homelab-automation.git',
    git_branch: desiredBranch,
  };
  if (!repository) repository = await api('/repositories', {
    method: 'POST',
    body: JSON.stringify(repositoryDesired),
  });
  for (const field of ['project_id', 'git_url', 'git_branch']) {
    if (repository[field] !== repositoryDesired[field]) {
      throw new Error(`Existing repository mismatch: ${field}`);
    }
  }

  const inventoryText = JSON.stringify({all: {hosts: {pi5: {
    ansible_host: '10.10.0.5',
    ansible_user: routeBootstrap.ansible_user,
    ansible_become: false,
    ansible_ssh_common_args: '-F /dev/null -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10',
  }}}});
  if (!inventory) inventory = await api('/inventory', {
    method: 'POST',
    body: JSON.stringify({
      name: inventoryName,
      project_id: 1,
      type: 'static',
      inventory: inventoryText,
      ssh_key_id: key.id,
      become_key_id: null,
    }),
  });
  if (inventory.ssh_key_id !== key.id || inventory.inventory !== inventoryText) {
    await api(`/inventory/${inventory.id}`, {
      method: 'PUT',
      body: JSON.stringify({...inventory, inventory: inventoryText, ssh_key_id: key.id}),
    });
    inventory = await api(`/inventory/${inventory.id}`);
  }

  const templateDesired = {
    name: templateName,
    project_id: 1,
    inventory_id: inventory.id,
    repository_id: repository.id,
    environment_id: 2,
    environment_ids: [2],
    app: 'ansible',
    arguments: '[]',
    git_branch: desiredBranch,
    playbook: 'automation/ansible/playbooks/backup-client-release.yml',
    description: 'Lock-aware release of the reviewed backup verifier on Pi5 only. No VM100 credential is enrolled.',
  };
  if (!template) template = await api('/templates', {
    method: 'POST',
    body: JSON.stringify(templateDesired),
  });
  for (const field of ['inventory_id', 'repository_id', 'git_branch', 'playbook']) {
    if (template[field] !== templateDesired[field]) {
      throw new Error(`Existing template mismatch: ${field}`);
    }
  }
  console.log(JSON.stringify({
    key_id: key.id,
    repository_id: repository.id,
    inventory_id: inventory.id,
    template_id: template.id,
    branch: desiredBranch,
    scope: 'pi5-only',
  }));
}
