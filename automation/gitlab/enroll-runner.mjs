import fs from 'node:fs/promises';

const base = 'https://gitlab.dungxbuif.com';
const description = 'vm100-rootless-homelab-automation';
const token = (await fs.readFile('credentials/gitlab-bootstrap-api-token', 'utf8')).trim();
async function api(path, options = {}) {
  const result = await fetch(`${base}/api/v4${path}`, {
    ...options,
    headers: { 'PRIVATE-TOKEN': token, 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(30000),
  });
  if (!result.ok) throw new Error(`GitLab ${options.method || 'GET'} ${path}: HTTP ${result.status}`);
  return result.json();
}

const project = await api('/projects/dungxbuif%2Fhomelab-automation');
if (project.visibility !== 'private') throw new Error('Refusing enrollment on non-private project');
const runners = await api(`/projects/${project.id}/runners?per_page=100`);
let runner = runners.find(item => item.description === description);
const credentialFile = 'credentials/gitlab-ci-runner.json';
if (runner) {
  const saved = JSON.parse(await fs.readFile(credentialFile, 'utf8'));
  if (saved.id !== runner.id || !saved.token) throw new Error('Existing runner credential missing or mismatched; do not create a duplicate');
} else {
  runner = await api('/user/runners', {
    method: 'POST',
    body: JSON.stringify({
      runner_type: 'project_type', project_id: project.id, description,
      paused: true, locked: true, run_untagged: true,
      tag_list: 'homelab-rootless', maximum_timeout: 7200,
      access_level: 'not_protected',
      maintenance_note: 'Private project only; independent rootless Docker on VM100; no production socket in jobs.',
    }),
  });
  await fs.writeFile(credentialFile, JSON.stringify(runner), { mode: 0o600, flag: 'wx' });
}
console.log(JSON.stringify({ project: project.path_with_namespace, project_id: project.id,
  runner_id: runner.id, registry: project.container_registry_image_prefix,
  credential_file: credentialFile, note: 'Inspect runner status before enabling; tokens never logged.' }));
