import { test } from 'node:test';
import assert from 'node:assert/strict';
import { enroll } from '../bootstrap-homepage-release.mjs';

function fixture() {
  const data = {'/users': [{role: 'owner'}], '/keys': [], '/inventory': [], '/templates': [], '/schedules': []};
  const writes = [];
  return {data, writes, api: async (path, body) => {
    if (body) {const item = {...body, id: writes.length + 1}; data[path].push(item); writes.push(item); return item;}
    return structuredClone(data[path]);
  }};
}
test('dry-run never reads private key or writes', async () => {
  const f = fixture();
  const result = await enroll(f.api, () => {throw Error('private key read');});
  assert.equal(result.mode, 'dry-run');
  assert.equal(f.writes.length, 0);
});
test('apply creates isolated resources and rerun is idempotent', async () => {
  const f = fixture();
  const result = await enroll(f.api, async () => 'test-key', true);
  assert.equal(result.template_id, 3);
  assert.equal(f.writes.length, 3);
  assert.equal(f.data['/inventory'][0].become_key_id, null);
  assert.match(f.data['/inventory'][0].inventory, /homelab-homepage-release/);
  await enroll(f.api, async () => {throw Error('duplicate key read');}, true);
  assert.equal(f.writes.length, 3);
});
test('non-owner membership blocks before creating key', async () => {
  const f = fixture(); f.data['/users'].push({role: 'task_runner'});
  await assert.rejects(enroll(f.api, async () => 'test-key', true), /owner-only/);
  assert.equal(f.writes.length, 0);
});
test('existing inventory drift is not overwritten', async () => {
  const f = fixture(); await enroll(f.api, async () => 'test-key', true);
  f.data['/inventory'][0].become_key_id = 99;
  await assert.rejects(enroll(f.api, async () => 'test-key', true), /inventory mismatch/);
  assert.equal(f.writes.length, 3);
});
test('duplicate template fails rather than selecting arbitrarily', async () => {
  const f = fixture(); await enroll(f.api, async () => 'test-key', true);
  f.data['/templates'].push({...f.data['/templates'][0], id: 99});
  await assert.rejects(enroll(f.api, async () => 'test-key', true), /Duplicate/);
});
test('existing environment drift is rejected', async () => {
  const f = fixture(); await enroll(f.api, async () => 'test-key', true);
  f.data['/templates'][0].environment_id = 99;
  f.data['/templates'][0].environment_ids = [99];
  await assert.rejects(enroll(f.api, async () => 'test-key', true), /environment/);
});
test('release schedules are rejected without deleting them', async () => {
  const f = fixture(); await enroll(f.api, async () => 'test-key', true);
  f.data['/schedules'].push({id: 4, template_id: 3});
  await assert.rejects(enroll(f.api, async () => 'test-key', true), /scheduled/);
  assert.equal(f.writes.length, 3);
  assert.equal(f.data['/schedules'].length, 1);
});
