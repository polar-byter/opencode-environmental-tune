'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class TextElement {
  constructor() {
    this.text = 'Old value';
    this.disabled = false;
  }

  get textContent() { return this.text; }
  set textContent(value) { this.text = String(value); }
  set innerHTML(value) { throw new Error('Use textContent, not innerHTML'); }
}

function checkRender(source, scenario, ids) {
  const known = ['render_fields', 'render_running', 'render_halted',
    'render_zero', 'render_literal', 'render_repeat'];
  assert.ok(known.includes(scenario), 'Unknown render scenario');
  const elements = new Map(ids.map((id) => [id, new TextElement()]));
  for (const id of ['title', 'status', 'event-count', 'runs', 'reworks',
    'failures', 'refresh', 'message']) {
    assert.ok(elements.has(id), `Missing HTML element: ${id}`);
  }
  elements.get('refresh').disabled = true;
  elements.get('message').textContent = 'Keep this message';
  const context = vm.createContext({
    document: { getElementById: (id) => elements.get(id) ?? null },
    fetch: () => { throw new Error('renderTask must not fetch'); },
  });
  vm.runInContext(source, context, { timeout: 1000 });
  const labels = {
    running: '\u0412 \u0440\u0430\u0431\u043e\u0442\u0435',
    halted: '\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0430',
    finished: '\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430',
  };
  let data = {
    title: 'Study', status: 'finished', event_count: 7, last_event_at: 140,
    work_runs: 3, green_work_runs: 2, reworks: 1, executor_failures: 4,
  };
  if (scenario === 'render_running') data.status = 'running';
  if (scenario === 'render_halted') data.status = 'halted';
  if (scenario === 'render_literal') data.title = '<b>Study</b>';
  if (scenario === 'render_zero') {
    data = { ...data, event_count: 0, work_runs: 0, green_work_runs: 0,
      reworks: 0, executor_failures: 0 };
  }

  function renderAndCheck(input) {
    const before = structuredClone(input);
    context.data = input;
    const result = vm.runInContext('renderTask(data)', context, { timeout: 1000 });
    assert.equal(result, undefined, 'Only update the page; no return value is needed');
    assert.deepEqual(input, before, 'Do not change the supplied summary');
    const expected = {
      title: before.title, status: labels[before.status],
      'event-count': String(before.event_count),
      runs: `${before.green_work_runs} / ${before.work_runs}`,
      reworks: String(before.reworks), failures: String(before.executor_failures),
    };
    for (const [id, text] of Object.entries(expected)) {
      assert.equal(elements.get(id).textContent, text, `Wrong text for ${id}`);
    }
    assert.equal(elements.get('refresh').disabled, true, 'Do not change the button');
    assert.equal(elements.get('message').textContent, 'Keep this message');
  }

  renderAndCheck(data);
  if (scenario === 'render_repeat') {
    renderAndCheck({ ...data, title: 'Updated task', status: 'running', event_count: 0,
      work_runs: 0, green_work_runs: 0, reworks: 0, executor_failures: 0 });
  }
}

async function check() {
  const { source, scenario, ids } = JSON.parse(fs.readFileSync(0, 'utf8'));
  if (scenario.startsWith('render_')) {
    checkRender(source, scenario, ids);
    return;
  }
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
