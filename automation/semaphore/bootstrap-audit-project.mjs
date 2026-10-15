import fs from 'node:fs/promises';

const apply = process.argv.includes('--apply');
if (process.argv.slice(2).some(arg => arg !== '--apply')) {
  throw new Error('Usage: node bootstrap-audit-project.mjs [--apply]');
}

const projectName = 'Homelab Audit';
const branch = 'codex/automation-bootstrap';
const sourceRepository = 'https://gitlab.dungxbuif.com/dungxbuif/homelab-automation.git';

function one(items, name, kind) {
  const matches = items.filter(item => item.name === name);
  if (matches.length > 1) throw new Error(`Duplicate ${kind}: ${name}`);
  return matches[0];
}

function inventoryText(target, address, user, keyFile) {
  return JSON.stringify({host_observers: {hosts: {[`${target}_observer`]: {
    ansible_host: address,
    ansible_user: user,
    ansible_become: false,
    ansible_ssh_common_args: `-o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -o IdentityFile={{ playbook_dir }}/../${keyFile} -o ConnectTimeout=10 -o UserKnownHostsFile={{ playbook_dir }}/../known_hosts`,
  }}}});
}

function templateDesired(name, inventoryId, playbook, description) {
  return {
    name,
    project_id: undefined,
    inventory_id: inventoryId,
    repository_id: undefined,
    environment_ids: [],
    app: 'ansible',
    arguments: '[]',
    git_branch: branch,
    playbook,
    description,
  };
}

function verifyKey(key, type, name) {
  if (!key) return;
  if (key.type !== type) throw new Error(`Existing key type mismatch: ${name}`);
}

function verifyInventory(inventory, key, text, name) {
  if (!inventory) return;
  if (!key || inventory.ssh_key_id !== key.id || inventory.inventory !== text || inventory.become_key_id != null) {
    throw new Error(`Existing inventory mismatch: ${name}`);
  }
}

function verifyTemplate(template, desired, inventory, repository, name) {
  if (!template) return;
  if (!inventory || template.inventory_id !== inventory.id) throw new Error(`Existing template inventory mismatch: ${name}`);
  if (!repository || template.repository_id !== repository.id) throw new Error(`Existing template repository mismatch: ${name}`);
  for (const field of ['git_branch', 'playbook', 'app', 'arguments']) {
    if (template[field] !== desired[field]) throw new Error(`Existing template mismatch: ${name}/${field}`);
  }
  if (JSON.stringify(template.environment_ids ?? []) !== '[]') throw new Error(`Existing template environment mismatch: ${name}`);
}

export async function enroll(api, readFile, shouldApply = false) {
  const projects = await api('/api/projects');
  const projectMatches = projects.filter(project => project.name === projectName);
  if (projectMatches.length > 1) throw new Error(`Duplicate project: ${projectName}`);
  let project = projectMatches[0];
  if (!shouldApply) return {mode: 'dry-run', project: project?.id ?? 'create'};

  if (!project) {
    project = await api('/api/projects', {
      name: projectName,
      alert: false,
      max_parallel_tasks: 1,
      type: 'ansible',
    });
  }
  if (!project?.id) throw new Error('Audit project did not return an id');
  const root = `/api/project/${project.id}`;
  const projectApi = (path, body) => api(`${root}${path}`, body);

  const keys = await projectApi('/keys');
  const repositories = await projectApi('/repositories');
  const inventories = await projectApi('/inventory');
  const templates = await projectApi('/templates');

  const sourceKeyName = 'Audit GitLab source (read only)';
  let sourceKey = one(keys, sourceKeyName, 'key');
  verifyKey(sourceKey, 'login_password', sourceKeyName);
  if (!sourceKey) {
    const source = JSON.parse(await readFile('credentials/gitlab-semaphore-source.json', 'utf8'));
    if (!source.username || !source.token || source.scopes?.join(',') !== 'read_repository') {
      throw new Error('Expected repository-only deploy credential');
    }
    sourceKey = await projectApi('/keys', {
      name: sourceKeyName,
      type: 'login_password',
      project_id: project.id,
      login_password: {login: source.username, password: source.token},
    });
  }

  const repositoryName = 'Homelab automation GitLab (audit)';
  let repository = one(repositories, repositoryName, 'repository');
  const repositoryDesired = {
    name: repositoryName,
    project_id: project.id,
    ssh_key_id: sourceKey.id,
    git_url: sourceRepository,
    git_branch: branch,
  };
  if (!repository) repository = await projectApi('/repositories', repositoryDesired);
  for (const field of ['project_id', 'ssh_key_id', 'git_url', 'git_branch']) {
    if (repository[field] !== repositoryDesired[field]) throw new Error(`Existing repository mismatch: ${field}`);
  }

  const hostTargets = [
    {id: 'vm100', label: 'VM100', address: '10.10.0.31', user: 'homelab-observer'},
    {id: 'pi5', label: 'Pi5', address: '10.10.0.5', user: 'homelab-observer'},
  ];
  const results = [];
  for (const target of hostTargets) {
    const keyName = `${target.label} audit host (read only)`;
    const inventoryName = `Audit ${target.label} host observer`;
    const templateName = `Audit ${target.label} runtime (read only)`;
    let key = one(keys, keyName, 'key');
    verifyKey(key, 'ssh', keyName);
    if (!key) key = await projectApi('/keys', {
      name: keyName,
      type: 'ssh',
      project_id: project.id,
      ssh: {login: target.user, private_key: await readFile('credentials/semaphore-host-audit', 'utf8')},
    });
    const text = inventoryText(target.id, target.address, target.user, 'host-audit.pub');
    let inventory = one(inventories, inventoryName, 'inventory');
    if (!inventory) inventory = await projectApi('/inventory', {
      name: inventoryName,
      project_id: project.id,
      type: 'static',
      inventory: text,
      ssh_key_id: key.id,
      become_key_id: null,
    });
    verifyInventory(inventory, key, text, inventoryName);
    let template = one(templates, templateName, 'template');
    const desired = templateDesired(
      templateName,
      inventory.id,
      'automation/semaphore/playbooks/host-audit.yml',
      `Read-only ${target.label} resources, containers, networks, listeners and SSH posture. Collection is not application or backup certification.`,
    );
    desired.project_id = project.id;
    desired.repository_id = repository.id;
    if (!template) template = await projectApi('/templates', desired);
    verifyTemplate(template, desired, inventory, repository, templateName);
    results.push({key_id: key.id, inventory_id: inventory.id, template_id: template.id, scope: `${target.id}-host-audit-only`});
  }

  const backupKeyName = 'Audit backup health (read only)';
  const backupInventoryName = 'Audit VM100 backup health observer';
  const backupTemplateName = 'Audit backup health (read only)';
  let backupKey = one(keys, backupKeyName, 'key');
  verifyKey(backupKey, 'ssh', backupKeyName);
  if (!backupKey) backupKey = await projectApi('/keys', {
    name: backupKeyName,
    type: 'ssh',
    project_id: project.id,
    ssh: {login: 'homelab-audit', private_key: await readFile('credentials/semaphore-backup-health', 'utf8')},
  });
  const backupText = inventoryText('vm100_health', '10.10.0.31', 'homelab-audit', 'backup-health.pub');
  let backupInventory = one(inventories, backupInventoryName, 'inventory');
  if (!backupInventory) backupInventory = await projectApi('/inventory', {
    name: backupInventoryName,
    project_id: project.id,
    type: 'static',
    inventory: backupText,
    ssh_key_id: backupKey.id,
    become_key_id: null,
  });
  verifyInventory(backupInventory, backupKey, backupText, backupInventoryName);
  let backupTemplate = one(templates, backupTemplateName, 'template');
  const backupDesired = templateDesired(
    backupTemplateName,
    backupInventory.id,
    'automation/semaphore/playbooks/backup-health.yml',
    'Read-only combined VM100/Pi backup health. A failed task is evidence for investigation, not an automatic repair.',
  );
  backupDesired.project_id = project.id;
  backupDesired.repository_id = repository.id;
  if (!backupTemplate) backupTemplate = await projectApi('/templates', backupDesired);
  verifyTemplate(backupTemplate, backupDesired, backupInventory, repository, backupTemplateName);
  results.push({key_id: backupKey.id, inventory_id: backupInventory.id, template_id: backupTemplate.id, scope: 'backup-health-only'});

  return {mode: 'applied', project_id: project.id, member_policy: 'admin-owner-only', resources: results};
}

async function main() {
  const base = 'https://semaphore.dungxbuif.com';
  const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
  const login = await fetch(`${base}/api/auth/login`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({auth: 'admin', password}),
    signal: AbortSignal.timeout(15000),
  });
  if (!login.ok) throw new Error(`Login HTTP ${login.status}`);
  const cookie = login.headers.getSetCookie().map(value => value.split(';')[0]).join('; ');
  async function api(path, body) {
    const response = await fetch(base + path, {
      method: body ? 'POST' : 'GET',
      headers: {cookie, 'Content-Type': 'application/json'},
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.status === 204 ? null : response.json();
  }
  console.log(JSON.stringify(await enroll(api, (path, encoding) => fs.readFile(path, encoding), apply)));
}

if (process.argv[1] && new URL(`file://${process.argv[1]}`).href === import.meta.url) await main();
