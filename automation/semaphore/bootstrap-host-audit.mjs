import fs from 'node:fs/promises';

const apply = process.argv.includes('--apply');
if (process.argv.slice(2).some(x => x !== '--apply')) throw Error('Usage: node bootstrap-host-audit.mjs [--apply]');
const base = 'https://semaphore.dungxbuif.com';
const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
const login = await fetch(base + '/api/auth/login', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({auth: 'admin', password}), signal: AbortSignal.timeout(15000),
});
if (!login.ok) throw Error(`Login HTTP ${login.status}`);
const cookie = login.headers.getSetCookie().map(x => x.split(';')[0]).join('; ');
async function api(path, body) {
  const response = await fetch(base + '/api/project/1' + path, {
    method: body ? 'POST' : 'GET', headers: {cookie, 'Content-Type': 'application/json'},
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw Error(`${path}: HTTP ${response.status}`);
  return response.json();
}
function existing(items, name) {
  const matches = items.filter(x => x.name === name);
  if (matches.length > 1) throw Error(`Duplicate resource: ${name}`);
  return matches[0];
}
const keyName = 'VM100 host audit only';
const inventoryName = 'Restricted VM100 host observer';
const templateName = 'Inspect VM100 runtime (read only)';
let key = existing(await api('/keys'), keyName);
let inventory = existing(await api('/inventory'), inventoryName);
let template = existing(await api('/templates'), templateName);
const inventoryText = JSON.stringify({host_observers: {hosts: {vm100_observer: {
  ansible_host: '10.10.0.31', ansible_user: 'homelab-observer', ansible_become: false,
  ansible_ssh_common_args: '-o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -o IdentityFile={{ playbook_dir }}/../host-audit.pub -o ConnectTimeout=10 -o UserKnownHostsFile={{ playbook_dir }}/../known_hosts',
}}}});
const desired = {
  name: templateName, project_id: 1, repository_id: 2,
  environment_id: 2, environment_ids: [2], app: 'ansible', arguments: '[]',
  git_branch: 'codex/automation-bootstrap', playbook: 'automation/semaphore/playbooks/host-audit.yml',
  description: 'Read-only VM100 resources, containers, networks and listeners. Successful collection does not certify application or backup health.',
};
function verify() {
  if (key && key.type !== 'ssh') throw Error('Existing key type mismatch');
  if (inventory && (!key || inventory.ssh_key_id !== key.id || inventory.inventory !== inventoryText || inventory.become_key_id != null)) throw Error('Existing inventory mismatch');
  if (template) {
    if (!inventory || template.inventory_id !== inventory.id) throw Error('Existing template inventory mismatch');
    for (const field of ['repository_id', 'git_branch', 'playbook', 'app', 'arguments']) {
      if (template[field] !== desired[field]) throw Error(`Existing template mismatch: ${field}`);
    }
  }
}
verify();
if (!apply) {
  console.log(JSON.stringify({mode: 'dry-run', key: key?.id ?? 'create', inventory: inventory?.id ?? 'create', template: template?.id ?? 'create'}));
} else {
  if (!key) key = await api('/keys', {
    name: keyName, type: 'ssh', project_id: 1,
    ssh: {login: 'homelab-observer', private_key: await fs.readFile('credentials/semaphore-host-audit', 'utf8')},
  });
  if (!inventory) inventory = await api('/inventory', {
    name: inventoryName, project_id: 1, type: 'static', inventory: inventoryText,
    ssh_key_id: key.id, become_key_id: null,
  });
  if (!template) template = await api('/templates', {...desired, inventory_id: inventory.id});
  verify();
  console.log(JSON.stringify({key_id: key.id, inventory_id: inventory.id, template_id: template.id, scope: 'host-audit-only'}));
}
