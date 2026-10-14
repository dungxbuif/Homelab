import fs from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const name = 'vm100-homelab-automation';

export async function enroll(api, credentialFile, apply = false) {
  const matches = (await api('/api/runners')).filter(item => item.name === name);
  if (matches.length > 1) throw new Error('Duplicate runner names; resolve before enrollment');
  if (matches.length) {
    const saved = JSON.parse(await fs.readFile(credentialFile, 'utf8'));
    if (saved.id !== matches[0].id || !saved.token || saved.name !== name) {
      throw new Error('Existing runner credential missing or mismatched');
    }
    return { action: 'reused', id: saved.id, name, active: matches[0].active };
  }
  if (!apply) return { action: 'would-create-inactive', name };
  // Reserve the path before mutation; ambiguous outcomes require reconciliation.
  try {
    await fs.writeFile(credentialFile, JSON.stringify({ name, state: 'pending' }), { mode: 0o600, flag: 'wx' });
  } catch (error) {
    if (error.code === 'EEXIST') throw new Error('Credential file already exists; reconcile previous enrollment');
    throw error;
  }
  const runner = await api('/api/runners', {
    method: 'POST',
    body: { name, active: false, registered: true, is_default: true, max_parallel_tasks: 1 },
  });
  if (!Number.isInteger(runner.id) || !runner.token || runner.active !== false) {
    throw new Error('Unexpected enrollment response; reconcile inactive runner before retrying');
  }
  await fs.writeFile(credentialFile, JSON.stringify({ name, id: runner.id, token: runner.token }), { mode: 0o600 });
  return { action: 'created-inactive', id: runner.id, name, active: false };
}

async function main() {
  if (process.argv.slice(2).some(arg => arg !== '--apply')) throw new Error('Usage: node enroll-runner.mjs [--apply]');
  const base = 'https://semaphore.dungxbuif.com';
  const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
  const login = await fetch(`${base}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ auth: 'admin', password }), signal: AbortSignal.timeout(15000),
  });
  if (!login.ok) throw new Error(`Semaphore login HTTP ${login.status}`);
  const cookie = login.headers.getSetCookie().map(item => item.split(';')[0]).join('; ');
  const api = async (route, options = {}) => {
    const response = await fetch(base + route, {
      method: options.method || 'GET', headers: { cookie, 'Content-Type': 'application/json' },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error(`Semaphore ${options.method || 'GET'} ${route}: HTTP ${response.status}`);
    return response.json();
  };
  console.log(JSON.stringify(await enroll(api, 'credentials/semaphore-runner.json', process.argv.includes('--apply'))));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
