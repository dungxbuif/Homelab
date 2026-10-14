import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { enroll } from '../enroll-runner.mjs';

async function fixture(fn) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'semaphore-enroll-'));
  try { await fn(path.join(dir, 'runner.json')); }
  finally { await fs.rm(dir, { recursive: true }); }
}

test('dry-run never creates runner or credential file', () => fixture(async file => {
  const result = await enroll(async () => [], file, false);
  assert.equal(result.action, 'would-create-inactive');
  await assert.rejects(fs.stat(file), { code: 'ENOENT' });
}));

test('creation stays inactive, protects token and reuses identity', () => fixture(async file => {
  let rows = [];
  let posts = 0;
  const api = async (route, options) => {
    assert.equal(route, '/api/runners');
    if (!options) return rows;
    posts++;
    assert.equal(options.body.active, false);
    assert.equal(options.body.max_parallel_tasks, 1);
    assert.equal(options.body.registered, true);
    rows = [{ ...options.body, id: 42 }];
    return { ...rows[0], token: 'test-only-token' };
  };
  const first = await enroll(api, file, true);
  const second = await enroll(api, file, true);
  assert.equal(first.id, second.id);
  assert.equal(posts, 1);
  assert.equal((await fs.stat(file)).mode & 0o777, 0o600);
  assert.equal(JSON.stringify(first).includes('test-only-token'), false);
}));

test('ambiguous creation cannot be retried automatically', () => fixture(async file => {
  const api = async (_route, options) => {
    if (!options) return [];
    throw new Error('connection lost');
  };
  await assert.rejects(enroll(api, file, true), /connection lost/);
  await assert.rejects(enroll(api, file, true), /already exists/);
}));

test('existing runner without matching credential is refused', () => fixture(async file => {
  await assert.rejects(enroll(async () => [{ id: 7, name: 'vm100-homelab-automation' }], file, true));
}));
