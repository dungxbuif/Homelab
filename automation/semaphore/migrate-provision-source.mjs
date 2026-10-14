import fs from 'node:fs/promises';
import { isDeepStrictEqual } from 'node:util';
import { pathToFileURL } from 'node:url';

const survey = ['engine', 'database_name', 'application', 'target_environment',
  'owner_role', 'owner_identity', 'policy_id', 'secret_ref'];
const playbook = 'automation/semaphore/playbooks/db-provision.yml';
const configuration = value => Object.fromEntries(Object.entries(value)
  .filter(([key]) => !['last_task', 'tasks', 'permissions'].includes(key)));

export async function migrate(api, saveRollback, apply = false) {
  const tasks = await api('/tasks');
  if (!Array.isArray(tasks) || tasks.some(task => !['success', 'error', 'stopped'].includes(task.status))) {
    throw new Error('Refusing source migration while a task is nonterminal');
  }
  const repo = await api('/repositories/2');
  if (repo.id !== 2 || repo.project_id !== 1 ||
      repo.git_url !== 'https://gitlab.dungxbuif.com/dungxbuif/homelab-automation.git' ||
      repo.git_branch !== 'codex/automation-bootstrap') throw new Error('Unexpected GitLab repository');
  const before = await api('/templates/1');
  if (before.id !== 1 || before.project_id !== 1 || before.inventory_id !== 1 || before.environment_id !== 1 ||
      !isDeepStrictEqual(before.survey_vars?.map(item => item.name).sort(), [...survey].sort())) {
    throw new Error('Unexpected provisioning template contract');
  }
  if (before.repository_id === 2 && before.playbook === playbook) return { action: 'already-migrated' };
  if (before.repository_id !== 1 || before.playbook !== 'playbooks/db-provision.yml') {
    throw new Error('Unexpected existing source; manual reconciliation required');
  }
  if (!apply) return { action: 'would-migrate', template_id: 1, repository_id: 2 };
  await saveRollback(before);
  const desired = { ...configuration(before), repository_id: 2, playbook };
  await api('/templates/1', { method: 'PUT', body: desired });
  const after = await api('/templates/1');
  for (const key of Object.keys(desired)) {
    if (!isDeepStrictEqual(after[key], desired[key])) {
      throw new Error(`Post-check mismatch: ${key}; inspect saved rollback before retrying`);
    }
  }
  return { action: 'migrated', template_id: 1, repository_id: 2, preserved_history: true };
}

async function main() {
  if (process.argv.slice(2).some(arg => arg !== '--apply')) throw new Error('Usage: node migrate-provision-source.mjs [--apply]');
  const base = 'https://semaphore.dungxbuif.com';
  const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
  const login = await fetch(base + '/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ auth: 'admin', password }), signal: AbortSignal.timeout(15000),
  });
  if (!login.ok) throw new Error(`Login HTTP ${login.status}`);
  const cookie = login.headers.getSetCookie().map(value => value.split(';')[0]).join('; ');
  const api = async (route, options = {}) => {
    const response = await fetch(base + '/api/project/1' + route, {
      method: options.method || 'GET', headers: { cookie, 'Content-Type': 'application/json' },
      body: options.body ? JSON.stringify(options.body) : undefined, signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error(`Semaphore ${route}: HTTP ${response.status}`);
    const text = await response.text();
    return text ? JSON.parse(text) : null;
  };
  const save = async value => fs.writeFile('credentials/semaphore-template-1-before-gitlab.json',
    JSON.stringify(value, null, 2), { mode: 0o600, flag: 'wx' });
  console.log(JSON.stringify(await migrate(api, save, process.argv.includes('--apply'))));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
