import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

export async function safeJson(response) {
  try { return await response.json(); }
  catch { throw Error('Invalid Semaphore JSON response'); }
}

const templates = {vm100: 4, pi5: 5};
const probes = ['kernel', 'memory', 'swap', 'disk', 'listeners', 'containers',
  'container_inventory', 'resource_limits', 'networks', 'swarm_services', 'resources'];

export function extractObservation(task, rows, host, now = Date.now()) {
  if (!Object.hasOwn(templates, host) || !Number.isSafeInteger(task?.id) || task.id < 1
      || task.template_id !== templates[host] || task.status !== 'success') {
    throw Error('Successful task from the fixed host-audit template required');
  }
  if (!Array.isArray(rows) || rows.some(row => typeof row.output !== 'string')) {
    throw Error('Invalid task output envelope');
  }
  const text = rows.map(row => row.output.replace(/\x1b\[[0-9;]*m/g, '')).join('\n');
  if (Buffer.byteLength(text) > 2 * 1024 * 1024) throw Error('Audit output exceeds bounded size');
  const reports = [];
  let pending = null;
  let alias;
  for (const line of text.split('\n')) {
    const start = /^ok: \[([a-z0-9_]+)\] => (\{.*)$/.exec(line);
    if (start) {
      if (pending !== null) throw Error('Truncated JSON report');
      alias = start[1];
      pending = start[2];
    } else if (pending !== null) pending += '\n' + line;
    if (pending === null) continue;
    let object;
    try { object = JSON.parse(pending); } catch { continue; }
    pending = null;
    if (Object.hasOwn(object, 'host_report')) reports.push({alias, report: object.host_report});
  }
  if (pending !== null || reports.length !== 1 || reports[0].alias !== `${host}_observer`) {
    throw Error('One complete matching host report required');
  }
  const report = reports[0].report;
  if (report?.schema_version !== 1 || report.scope !== 'host_runtime_only'
      || report.collection_complete !== true || report.inventory_complete !== false) {
    throw Error('Incomplete or unsupported observation scope');
  }
  const timestamp = report.observed_at;
  const age = now - Date.parse(timestamp);
  if (typeof timestamp !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(timestamp)
      || !Number.isFinite(age) || age < 0 || age > 900_000) {
    throw Error('Observation must be timezone-aware and less than 15 minutes old');
  }
  if (!report.probes || probes.some(name => typeof report.probes[name]?.output !== 'string'
      || Object.hasOwn(report.probes[name], 'error'))) {
    throw Error('Missing or failed required probe');
  }
  return {schema_version: 1, host, task_id: task.id, template_id: task.template_id,
    observed_at: timestamp, scope: 'host_runtime_only', inventory_complete: false, report};
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 6 || args[0] !== '--task' || args[2] !== '--host' || args[4] !== '--output') {
    throw Error('Usage: export-host-audit.mjs --task ID --host pi5|vm100 --output ABSOLUTE_NEW_FILE');
  }
  const taskId = Number(args[1]), host = args[3], output = args[5];
  if (!Number.isSafeInteger(taskId) || taskId < 1 || !Object.hasOwn(templates, host) || !path.isAbsolute(output)) {
    throw Error('Invalid task, host or output path');
  }
  const parent = await fs.lstat(path.dirname(output));
  if (!parent.isDirectory() || parent.isSymbolicLink() || parent.uid !== process.getuid()
      || (parent.mode & 0o777) !== 0o700) throw Error('Output directory must be owned and mode 0700');
  const base = 'https://semaphore.dungxbuif.com/api';
  const password = (await fs.readFile('credentials/semaphore-admin-password', 'utf8')).trim();
  const login = await fetch(base + '/auth/login', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({auth: 'admin', password}),
    signal: AbortSignal.timeout(20_000)});
  if (!login.ok) throw Error(`Semaphore login HTTP ${login.status}`);
  const cookie = login.headers.getSetCookie().map(value => value.split(';')[0]).join('; ');
  async function get(suffix) {
    const response = await fetch(base + `/project/1/tasks/${taskId}` + suffix,
      {headers: {cookie}, signal: AbortSignal.timeout(20_000)});
    if (!response.ok) throw Error(`Semaphore read HTTP ${response.status}`);
    return safeJson(response);
  }
  const task = await get('');
  if (task.id !== taskId) throw Error('Task identity mismatch');
  const evidence = extractObservation(task, await get('/output'), host);
  const writer = fileURLToPath(new URL('../scripts/write-private-artifact.py', import.meta.url));
  const result = spawnSync('python3', [writer, output], {
    input: JSON.stringify(evidence, null, 2) + '\n', timeout: 20_000,
    maxBuffer: 4096, encoding: 'utf8',
  });
  if (result.error || result.status !== 0) throw Error('Private artifact write failed');
  console.log(JSON.stringify({host, task_id: taskId, output, scope: evidence.scope,
    inventory_complete: false}));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(() => { console.error('Host audit export failed; verify task, API access and private output path'); process.exitCode = 1; });
}
