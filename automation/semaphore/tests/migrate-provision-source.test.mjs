import { test } from 'node:test';
import assert from 'node:assert/strict';
import { migrate } from '../migrate-provision-source.mjs';

const names = ['engine', 'database_name', 'application', 'target_environment',
  'owner_role', 'owner_identity', 'policy_id', 'secret_ref'];
function fixture() {
  let template = { id: 1, project_id: 1, repository_id: 1, playbook: 'playbooks/db-provision.yml',
    inventory_id: 1, environment_id: 1, survey_vars: names.map(name => ({ name })), name: 'Existing' };
  const calls = [];
  const state = { tasks: [{ status: 'success' }], saved: null, calls };
  state.api = async (route, options) => {
    calls.push([route, options]);
    if (route === '/tasks') return state.tasks;
    if (route === '/repositories/2') return { id: 2, project_id: 1,
      git_url: 'https://gitlab.dungxbuif.com/dungxbuif/homelab-automation.git',
      git_branch: 'codex/automation-bootstrap' };
    if (route === '/templates/1') {
      if (options) { assert.ok(state.saved); template = structuredClone(options.body); }
      return structuredClone(template);
    }
    throw Error(route);
  };
  state.save = async value => { state.saved = structuredClone(value); };
  return state;
}
test('dry run makes no writes or backup', async () => {
  const f = fixture();
  assert.equal((await migrate(f.api, f.save)).action, 'would-migrate');
  assert.equal(f.saved, null);
  assert.ok(f.calls.every(([, options]) => !options));
});
test('migration preserves survey and settings, verifies and is idempotent', async () => {
  const f = fixture();
  assert.equal((await migrate(f.api, f.save, true)).action, 'migrated');
  const changed = await f.api('/templates/1');
  assert.deepEqual(changed, { ...f.saved, repository_id: 2,
    playbook: 'automation/semaphore/playbooks/db-provision.yml' });
  assert.equal((await migrate(f.api, f.save, true)).action, 'already-migrated');
  assert.equal(f.calls.filter(([, options]) => options).length, 1);
});
for (const status of ['running', 'waiting', 'starting', 'unknown']) {
  test(`refuses nonterminal task ${status}`, async () => {
    const f = fixture(); f.tasks = [{ status }];
    await assert.rejects(migrate(f.api, f.save, true), /nonterminal/);
    assert.equal(f.saved, null);
  });
}

test('server-derived task summary is not written as configuration', async () => {
  const f = fixture();
  const api = async (route, options) => {
    const value = await f.api(route, options);
    if (route === '/templates/1') return { ...value, last_task: { tpl_playbook: value.playbook }, tasks: 6 };
    return value;
  };
  assert.equal((await migrate(api, f.save, true)).action, 'migrated');
  const body = f.calls.find(([, options]) => options)[1].body;
  assert.equal('last_task' in body, false);
  assert.equal('tasks' in body, false);
});
