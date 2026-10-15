import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const script = path.join(root, 'automation/semaphore/bootstrap-backup-client-release.mjs');

function run(args = []) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, ...args], {cwd: root, env: {...process.env, NODE_OPTIONS: '--no-warnings'}});
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (code) => resolve({code, stdout, stderr}));
  });
}

test('bootstrap script has an explicit dry-run path and no secret output', async () => {
  const source = await fs.readFile(script, 'utf8');
  assert.match(source, /scope: 'pi5-only'/);
  assert.match(source, /codex\/relayhub-source-foundation/);
  assert.match(source, /Release backup client \(Pi5\)/);
  assert.match(source, /Pi5 backup client release \(SSH\)/);
  assert.match(source, /type: 'ssh'/);
  assert.match(source, /automation\/semaphore\/playbooks\/backup-client-release\.yml/);
  assert.doesNotMatch(source, /console\.log\([^\n]*ansible_password/);
});

test('bootstrap script rejects unknown arguments before login', async () => {
  const result = await run(['--unexpected']);
  assert.notEqual(result.code, 0);
  assert.match(result.stderr, /Usage: node bootstrap-backup-client-release\.mjs/);
});
