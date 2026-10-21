import assert from 'node:assert/strict';
import test from 'node:test';

const moduleUrl = new URL('../export-host-audit.mjs', import.meta.url);
const now = Date.parse('2026-10-15T04:40:00Z');
const probeNames = ['kernel', 'memory', 'swap', 'disk', 'listeners', 'containers',
  'container_inventory', 'resource_limits', 'networks', 'swarm_services', 'resources'];
function fixture() {
  const report = {schema_version: 1, scope: 'host_runtime_only', collection_complete: true,
    inventory_complete: false, observed_at: '2026-10-15T04:39:00+00:00',
    probes: Object.fromEntries(probeNames.map(name => [name, {output: ''}]))};
  const rows = [{output: 'unrelated startup log'}, ...(`ok: [vm100_observer] => ${JSON.stringify({host_report: report}, null, 2)}`)
    .split('\n').map(output => ({output: `\x1b[0;32m${output}\x1b[0m`}))];
  return {task: {id: 40, template_id: 4, status: 'success'}, report, rows};
}
test('exports observed evidence with task provenance, without claiming global completeness', async () => {
  const {extractObservation} = await import(moduleUrl);
  const {task, rows} = fixture();
  const result = extractObservation(task, rows, 'vm100', now);
  assert.equal(result.host, 'vm100');
  assert.equal(result.task_id, 40);
  assert.equal(result.inventory_complete, false);
  assert.equal(result.report.scope, 'host_runtime_only');
  assert.equal(JSON.stringify(result).includes('unrelated startup log'), false);
});
test('rejects failed and mismatched task provenance', async () => {
  const {extractObservation} = await import(moduleUrl);
  for (const changes of [{status: 'running'}, {template_id: 5}, {id: '40'}]) {
    const {task, rows} = fixture();
    assert.throws(() => extractObservation({...task, ...changes}, rows, 'vm100', now));
  }
});
test('rejects truncated and duplicate reports', async () => {
  const {extractObservation} = await import(moduleUrl);
  const {task, rows} = fixture();
  assert.throws(() => extractObservation(task, rows.slice(0, -1), 'vm100', now));
  assert.throws(() => extractObservation(task, [...rows, ...rows], 'vm100', now));
});
test('rejects incomplete collection, missing probes and invalid observation time', async () => {
  const {extractObservation} = await import(moduleUrl);
  for (const change of [
    {collection_complete: false}, {inventory_complete: true}, {probes: {}},
    {observed_at: '2020-01-01T00:00:00Z'}, {observed_at: '2027-01-01T00:00:00Z'},
    {observed_at: '2026-10-15T04:39:00'},
  ]) {
    const {task, report} = fixture();
    const rows = [{output: `ok: [vm100_observer] => ${JSON.stringify({host_report: {...report, ...change}})}`}];
    assert.throws(() => extractObservation(task, rows, 'vm100', now));
  }
});
test('malformed API JSON never exposes response contents', async () => {
  const {safeJson} = await import(moduleUrl);
  assert.equal(typeof safeJson, 'function');
  await assert.rejects(() => safeJson({json: async () => { throw Error('PRIVATE_SENTINEL'); }}),
    error => error.message === 'Invalid Semaphore JSON response');
});
