import test from 'node:test';
import assert from 'node:assert/strict';
import {isDenied, requireStatus} from '../rbac-live-check.mjs';

test('denied status accepts auth and project-isolation responses', () => {
  for (const status of [401, 403, 404]) assert.equal(isDenied(status), true);
  for (const status of [200, 201, 500]) assert.equal(isDenied(status), false);
});

test('status assertion is strict for allowed reads', () => {
  assert.deepEqual(requireStatus({status: 200}, 200, 'read'), {label: 'read', status: 200, ok: true});
  assert.throws(() => requireStatus({status: 403}, 200, 'read'), /expected 200, got HTTP 403/);
});

test('status assertion accepts only the documented denied range', () => {
  assert.equal(requireStatus({status: 403}, 'denied', 'write').ok, true);
  assert.throws(() => requireStatus({status: 200}, 'denied', 'write'), /expected denied, got HTTP 200/);
});
