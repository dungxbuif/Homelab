import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

export async function enroll(api, readKey, apply = false) {
  const members = await api('/users');
  if (!members.length || members.some(x => x.role !== 'owner')) throw Error('Release project must remain owner-only until role isolation is configured');
  function existing(items, name) {
    const matches = items.filter(x => x.name === name);
    if (matches.length > 1) throw Error(`Duplicate resource: ${name}`);
    return matches[0];
  }
  const keyName = 'Homepage approved digest release only';
  const inventoryName = 'Restricted Homepage release on Pi5';
  const templateName = 'Release approved Homepage';
  let key = existing(await api('/keys'), keyName);
  let inventory = existing(await api('/inventory'), inventoryName);
  let template = existing(await api('/templates'), templateName);
  const schedules = await api('/schedules');
  const inventoryText = JSON.stringify({homepage_releasers: {hosts: {pi5_homepage_release: {
    ansible_host: '10.10.0.5', ansible_user: 'homelab-homepage-release', ansible_become: false,
    ansible_ssh_common_args: '-o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -o IdentityFile={{ playbook_dir }}/../homepage-release.pub -o ConnectTimeout=10 -o UserKnownHostsFile={{ playbook_dir }}/../known_hosts',
  }}}});
  const desired = {
    name: templateName, project_id: 1, repository_id: 2,
    environment_id: 2, environment_ids: [2], app: 'ansible', arguments: '[]',
    git_branch: 'codex/automation-bootstrap', playbook: 'automation/semaphore/playbooks/homepage-release.yml',
    description: 'Manual release of the root-approved Homepage digest only. Failed or rolled-back releases remain failed tasks. Owner-only project; no arbitrary images or host commands.',
  };
  function verify() {
    if (key && key.type !== 'ssh') throw Error('Existing key type mismatch');
    if (inventory && (!key || inventory.ssh_key_id !== key.id || inventory.inventory !== inventoryText || inventory.become_key_id != null)) throw Error('Existing inventory mismatch');
    if (template) {
      if (!inventory || template.inventory_id !== inventory.id) throw Error('Existing template inventory mismatch');
      if (template.environment_id !== 2 || JSON.stringify(template.environment_ids) !== '[2]') throw Error('Existing template environment mismatch');
      if (schedules.some(x => x.template_id === template.id)) throw Error('Homepage release must not be scheduled');
      for (const field of ['repository_id', 'git_branch', 'playbook', 'app', 'arguments']) {
        if (template[field] !== desired[field]) throw Error(`Existing template mismatch: ${field}`);
      }
    }
  }
  verify();
  if (!apply) return {mode: 'dry-run', key: key?.id ?? 'create', inventory: inventory?.id ?? 'create', template: template?.id ?? 'create'};
  if (!key) key = await api('/keys', {
    name: keyName, type: 'ssh', project_id: 1,
    ssh: {login: 'homelab-homepage-release', private_key: await readKey()},
  });
  if (!inventory) inventory = await api('/inventory', {
    name: inventoryName, project_id: 1, type: 'static', inventory: inventoryText,
    ssh_key_id: key.id, become_key_id: null,
  });
  if (!template) template = await api('/templates', {...desired, inventory_id: inventory.id});
  verify();
  return {key_id: key.id, inventory_id: inventory.id, template_id: template.id, scope: 'approved-homepage-digest-only'};
}

async function main() {
  if (process.argv.slice(2).some(x => x !== '--apply')) throw Error('Usage: node bootstrap-homepage-release.mjs [--apply]');
  const base = 'https://semaphore.dungxbuif.com';
  const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
  const login = await fetch(base + '/api/auth/login', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({auth: 'admin', password}), signal: AbortSignal.timeout(15000),
  });
  if (!login.ok) throw Error(`Login HTTP ${login.status}`);
  const cookie = login.headers.getSetCookie().map(x => x.split(';')[0]).join('; ');
  const api = async (path, body) => {
    const response = await fetch(base + '/api/project/1' + path, {
      method: body ? 'POST' : 'GET', headers: {cookie, 'Content-Type': 'application/json'},
      body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw Error(`${path}: HTTP ${response.status}`);
    return response.json();
  };
  const result = await enroll(api, () => fs.readFile('credentials/semaphore-homepage-release', 'utf8'), process.argv.includes('--apply'));
  console.log(JSON.stringify(result));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
