'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function check() {
  const { source, scenario } = JSON.parse(fs.readFileSync(0, 'utf8'));
  const summary = {
    title: 'Study', status: 'finished', event_count: 5, last_event_at: 140,
    work_runs: 1, green_work_runs: 1, reworks: 0, executor_failures: 0,
  };
  const updated = { ...summary, event_count: 6 };
  const messages = { http400: 'no events yet', http500: 'cannot read journal or page' };
  const known = ['success', 'http400', 'http500', 'network', 'json', 'fresh'];
  assert.ok(known.includes(scenario), 'Unknown test scenario');
  const failure = scenario === 'json' ? new SyntaxError('invalid JSON') :
    new TypeError('Failed to fetch');
  const calls = [];
  let requestCount = 0;
  const context = vm.createContext({
    fetch: async (url) => {
      assert.equal(url, '/api/task');
      calls.push('fetch');
      requestCount += 1;
      if (scenario === 'network') throw failure;
      const data = scenario in messages ? { error: messages[scenario] } :
        requestCount === 1 ? summary : updated;
      return {
        ok: !(scenario in messages),
        status: scenario === 'http400' ? 400 : scenario === 'http500' ? 500 : 200,
        json: async () => {
          calls.push('json');
          if (scenario === 'json') throw failure;
          return data;
        },
      };
    },
  });
  vm.runInContext(source, context, { timeout: 1000 });
  const load = () => vm.runInContext('loadTask()', context, { timeout: 1000 });

  if (scenario in messages) {
    await assert.rejects(load, { name: 'Error', message: messages[scenario] });
  } else if (scenario === 'network' || scenario === 'json') {
    await assert.rejects(load, (error) => error === failure);
  } else {
    assert.strictEqual(await load(), summary, 'Return the parsed summary object');
    if (scenario === 'fresh') {
      assert.strictEqual(await load(), updated, 'Read fresh data on every call');
    }
  }
  const expected = scenario === 'network' ? ['fetch'] :
    scenario === 'fresh' ? ['fetch', 'json', 'fetch', 'json'] : ['fetch', 'json'];
  assert.deepEqual(calls, expected);
}

check().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
