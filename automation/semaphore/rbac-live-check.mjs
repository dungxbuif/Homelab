#!/usr/bin/env node
/**
 * Read-only Semaphore Community RBAC acceptance probe.
 *
 * Credentials are supplied only through the environment. The default mode
 * never creates a task or mutates a project; --execute is an explicit opt-in
 * for one read-only audit task after project isolation has been verified.
 */

import process from 'node:process';

export const deniedStatuses = new Set([401, 403, 404]);

export function isDenied(status) {
  return deniedStatuses.has(status);
}

export function requireStatus(result, expected, label) {
  const ok = expected === 'denied' ? isDenied(result.status) : result.status === expected;
  if (!ok) throw new Error(`${label}: expected ${expected}, got HTTP ${result.status}`);
  return {label, status: result.status, ok: true};
}

function usage() {
  return 'SEMAPHORE_RBAC_USERNAME=... SEMAPHORE_RBAC_PASSWORD=... node automation/semaphore/rbac-live-check.mjs [--execute]';
}

export async function login(base, username, password, fetchImpl = fetch) {
  const response = await fetchImpl(`${base}/api/auth/login`, {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({auth: username, password}),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok && response.status !== 204) throw new Error(`login failed: HTTP ${response.status}`);
  const cookies = response.headers.getSetCookie?.() ?? [];
  if (!cookies.length) throw new Error('login did not return a session cookie');
  return cookies.map(value => value.split(';', 1)[0]).join('; ');
}

export async function request(base, cookie, path, options = {}, fetchImpl = fetch) {
  const response = await fetchImpl(`${base}${path}`, {
    ...options,
    headers: {'content-type': 'application/json', cookie, ...(options.headers ?? {})},
    signal: AbortSignal.timeout(15000),
  });
  return {status: response.status, body: await response.text()};
}

async function runAuditTask(base, cookie, projectId, templateId, fetchImpl) {
  const task = await request(base, cookie, `/api/project/${projectId}/tasks`, {
    method: 'POST',
    body: JSON.stringify({template_id: templateId, message: 'RBAC read-only acceptance probe'}),
  }, fetchImpl);
  if (![200, 201].includes(task.status)) throw new Error(`audit task start failed: HTTP ${task.status}`);
  const created = JSON.parse(task.body);
  if (!Number.isInteger(created.id) || created.id <= 0) throw new Error('audit task response has no valid id');
  return {task_id: created.id, status: task.status};
}

export async function runChecks({
  base = process.env.SEMAPHORE_BASE_URL ?? 'https://semaphore.dungxbuif.com',
  username = process.env.SEMAPHORE_RBAC_USERNAME,
  password = process.env.SEMAPHORE_RBAC_PASSWORD,
  auditProjectId = Number(process.env.SEMAPHORE_AUDIT_PROJECT_ID ?? 2),
  productionProjectId = Number(process.env.SEMAPHORE_PRODUCTION_PROJECT_ID ?? 1),
  auditTemplateId = Number(process.env.SEMAPHORE_AUDIT_TEMPLATE_ID ?? 9),
  execute = false,
  fetchImpl = fetch,
} = {}) {
  if (!username || !password) throw new Error('missing SEMAPHORE_RBAC_USERNAME/PASSWORD');
  if (![auditProjectId, productionProjectId, auditTemplateId].every(Number.isInteger)) throw new Error('project/template IDs must be integers');
  const cookie = await login(base, username, password, fetchImpl);
  const results = [];

  const me = await request(base, cookie, '/api/user', {}, fetchImpl);
  if (me.status !== 200) throw new Error(`identity lookup failed: HTTP ${me.status}`);
  const identity = JSON.parse(me.body);
  if (identity.admin === true) throw new Error('RBAC probe must use a non-admin account');
  results.push({label: 'non-admin identity', status: me.status, ok: true});

  results.push(requireStatus(
    await request(base, cookie, `/api/project/${auditProjectId}/templates`, {}, fetchImpl),
    200, 'audit project readable'));
  results.push(requireStatus(
    await request(base, cookie, `/api/project/${productionProjectId}/keys`, {}, fetchImpl),
    'denied', 'production key list denied'));
  results.push(requireStatus(
    await request(base, cookie, `/api/project/${productionProjectId}/inventory`, {}, fetchImpl),
    'denied', 'production inventory denied'));
  results.push(requireStatus(
    await request(base, cookie, `/api/project/${productionProjectId}/templates/1`, {}, fetchImpl),
    'denied', 'production template denied'));

  if (execute) {
    results.push(await runAuditTask(base, cookie, auditProjectId, auditTemplateId, fetchImpl));
  }
  return {base, username: identity.username, admin: identity.admin, execute, results};
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const execute = process.argv.includes('--execute');
  if (process.argv.some(arg => arg !== '--execute' && arg !== process.argv[0] && arg !== process.argv[1])) {
    console.error(usage());
    process.exit(2);
  }
  runChecks({execute}).then(result => {
    console.log(JSON.stringify(result));
  }).catch(error => {
    console.error(error.message);
    process.exit(1);
  });
}
