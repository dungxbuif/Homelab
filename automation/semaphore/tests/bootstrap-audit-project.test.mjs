import assert from 'node:assert/strict';
import test from 'node:test';
import {enroll} from '../bootstrap-audit-project.mjs';

function fixture() {
  const data = {'/api/projects': [], '/api/project/42/keys': [], '/api/project/42/repositories': [],
    '/api/project/42/inventory': [], '/api/project/42/templates': []};
  const writes = [];
  const api = async (path, body) => {
    if (body) {
      if (path === '/api/projects') {
        const project = {...body, id: 42};
        data['/api/projects'].push(project);
        writes.push({path, body});
        return project;
      }
      const item = {...body, id: writes.length + 1};
      data[path].push(item);
      writes.push({path, body});
      return item;
    }
    return structuredClone(data[path]);
  };
  const readFile = async path => {
    if (path.endsWith('gitlab-semaphore-source.json')) return JSON.stringify({username: 'svc', token: 'secret', scopes: ['read_repository']});
    return 'private-key';
  };
  return {data, writes, api, readFile};
}

test('dry-run does not read credentials or create a project', async () => {
  const f = fixture();
  const result = await enroll(f.api, () => {throw Error('credential read');});
  assert.deepEqual(result, {mode: 'dry-run', project: 'create'});
  assert.equal(f.writes.length, 0);
});

test('apply creates only read-only audit resources and rerun is idempotent', async () => {
  const f = fixture();
  const result = await enroll(f.api, f.readFile, true);
  assert.equal(result.mode, 'applied');
  assert.equal(result.member_policy, 'admin-owner-only');
  assert.equal(result.resources.length, 3);
  assert.equal(f.writes.filter(write => write.path === '/api/projects').length, 1);
  assert.equal(f.writes.filter(write => write.path.endsWith('/keys')).length, 4);
  assert.equal(f.writes.filter(write => write.path.endsWith('/repositories')).length, 1);
  assert.equal(f.writes.filter(write => write.path.endsWith('/inventory')).length, 3);
  assert.equal(f.writes.filter(write => write.path.endsWith('/templates')).length, 3);
  const before = f.writes.length;
  await enroll(f.api, () => {throw Error('duplicate credential read');}, true);
  assert.equal(f.writes.length, before);
});

test('existing resource drift aborts without deleting anything', async () => {
  const f = fixture();
  await enroll(f.api, f.readFile, true);
  const before = f.writes.length;
  f.data['/api/project/42/inventory'][0].become_key_id = 99;
  await assert.rejects(enroll(f.api, f.readFile, true), /inventory mismatch/);
  assert.equal(f.writes.length, before);
});

test('duplicate project names abort before credentials are read', async () => {
  const f = fixture();
  f.data['/api/projects'].push({id: 7, name: 'Homelab Audit'});
  f.data['/api/projects'].push({id: 8, name: 'Homelab Audit'});
  await assert.rejects(enroll(f.api, () => {throw Error('must not read');}, true), /Duplicate project/);
});
