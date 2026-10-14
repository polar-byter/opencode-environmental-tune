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

async function checkRefresh(source, scenario, ids) {
  const known = ['refresh_pending', 'refresh_success', 'refresh_load_error',
    'refresh_render_error', 'refresh_retry', 'refresh_repeat'];
  assert.ok(known.includes(scenario), 'Unknown refresh scenario');
  const elements = new Map(ids.map((id) => [id, new TextElement()]));
  const button = elements.get('refresh');
  const message = elements.get('message');
  assert.ok(button && message, 'Refresh button and message must exist');
  message.textContent = 'Previous error';
  const context = vm.createContext({
    document: { getElementById: (id) => elements.get(id) ?? null },
    fetch: () => { throw new Error('Use loadTask instead of a direct fetch'); },
  });
  vm.runInContext(source, context, { timeout: 1000 });
  const summary = { title: 'Study', status: 'finished', event_count: 5,
    work_runs: 1, green_work_runs: 1, reworks: 0, executor_failures: 0 };
  const original = structuredClone(summary);
  const updated = { ...summary, event_count: 6 };
  const failure = new Error('<b>Connection failed</b>');
  const rendered = [];
  const calls = [];
  let loadCount = 0;
  let release;
  context.loadTask = async () => {
    assert.equal(button.disabled, true, 'Disable the button before loading');
    calls.push('load');
    loadCount += 1;
    if (scenario === 'refresh_pending') {
      return new Promise((resolve) => { release = resolve; });
    }
    if (scenario === 'refresh_load_error' ||
        (scenario === 'refresh_retry' && loadCount === 1)) throw failure;
    return loadCount === 1 ? summary : updated;
  };
  context.renderTask = (data) => {
    assert.equal(button.disabled, true, 'Keep the button disabled while rendering');
    calls.push('render');
    if (scenario === 'refresh_render_error') throw failure;
    rendered.push(data);
  };
  const refresh = () => vm.runInContext('refreshTask()', context, { timeout: 1000 });
  const first = refresh();

  if (scenario === 'refresh_pending') {
    const disabledDuringLoad = button.disabled;
    const textDuringLoad = message.textContent;
    const renderedDuringLoad = rendered.length;
    release(summary);
    assert.equal(await first, undefined);
    assert.equal(disabledDuringLoad, true);
    assert.equal(textDuringLoad, '', 'Clear the old message before awaiting data');
    assert.equal(renderedDuringLoad, 0, 'Await loadTask before rendering');
  } else {
    assert.equal(await first, undefined, 'Handle errors without returning summary data');
  }
  assert.equal(button.disabled, false, 'Enable the button after success or failure');

  if (scenario === 'refresh_load_error' || scenario === 'refresh_render_error') {
    assert.equal(message.textContent, failure.message, 'Show the error as literal text');
    assert.deepEqual(calls, scenario === 'refresh_load_error' ? ['load'] : ['load', 'render']);
    assert.equal(rendered.length, 0);
  } else if (scenario === 'refresh_retry') {
    assert.equal(message.textContent, failure.message);
    assert.equal(rendered.length, 0);
    assert.equal(await refresh(), undefined);
    assert.equal(button.disabled, false);
    assert.equal(message.textContent, '', 'Remove the old error on a successful retry');
    assert.deepEqual(calls, ['load', 'load', 'render']);
    assert.strictEqual(rendered[0], updated);
  } else {
    assert.equal(message.textContent, '', 'A successful refresh must clear old errors');
    assert.deepEqual(calls, ['load', 'render']);
    assert.strictEqual(rendered[0], summary);
    if (scenario === 'refresh_repeat') {
      assert.equal(await refresh(), undefined);
      assert.deepEqual(calls, ['load', 'render', 'load', 'render']);
      assert.strictEqual(rendered[1], updated);
      assert.equal(button.disabled, false);
    }
  }
  assert.deepEqual(summary, original, 'Do not change the loaded summary');
}

function checkMain(source, scenario, ids) {
  const known = ['main_listener', 'main_initial', 'main_click', 'main_local'];
  assert.ok(known.includes(scenario), 'Unknown main scenario');
  assert.ok(ids.includes('refresh'), 'Refresh button must exist');
  const calls = [];
  let listener;
  let refreshCount = 0;
  const button = {
    addEventListener: (event, callback) => {
      assert.equal(event, 'click');
      assert.equal(typeof callback, 'function', 'Pass a function, not its call result');
      assert.equal(listener, undefined, 'Register one listener');
      listener = callback;
      calls.push('listen');
    },
  };
  const context = vm.createContext({
    document: {
      getElementById: (id) => {
        assert.equal(id, 'refresh');
        calls.push('find');
        return button;
      },
    },
    fetch: () => { throw new Error('main must call refreshTask, not fetch'); },
  });
  vm.runInContext(source, context, { timeout: 1000 });
  const before = Object.keys(context).sort();
  context.refreshTask = () => {
    refreshCount += 1;
    calls.push('refresh');
  };
  assert.equal(vm.runInContext('main()', context, { timeout: 1000 }), undefined);
  assert.deepEqual(calls, ['find', 'listen', 'refresh']);
  assert.equal(refreshCount, 1, 'Refresh once on startup');
  assert.strictEqual(listener, context.refreshTask, 'Use the existing refreshTask as callback');
  if (scenario === 'main_click') {
    listener({ type: 'click' });
    assert.equal(refreshCount, 2, 'A click must start a fresh refresh');
    assert.deepEqual(calls, ['find', 'listen', 'refresh', 'refresh']);
  }
  if (scenario === 'main_local') {
    assert.deepEqual(Object.keys(context).sort(), before, 'Keep local variables inside main');
  }
}

async function checkStartup(source, scenario, ids) {
  assert.ok(['startup_initial', 'startup_click', 'startup_retry'].includes(scenario));
  const elements = new Map(ids.map((id) => [id, new TextElement()]));
  const button = elements.get('refresh');
  const message = elements.get('message');
  assert.ok(button && message, 'Refresh button and message must exist');
  let listener;
  let registrations = 0;
  button.addEventListener = (event, callback) => {
    assert.equal(event, 'click');
    assert.equal(typeof callback, 'function');
    registrations += 1;
    listener = callback;
  };
  let requests = 0;
  const context = vm.createContext({
    document: { getElementById: (id) => elements.get(id) ?? null },
    fetch: async (url) => {
      assert.equal(url, '/api/task');
      requests += 1;
      const failed = scenario === 'startup_retry' && requests === 1;
      const data = failed ? { error: 'cannot read journal or page' } : {
        title: requests === 1 ? 'Initial task' : 'Updated task',
        status: 'finished', event_count: requests === 1 ? 5 : 6,
        work_runs: 1, green_work_runs: 1, reworks: 0, executor_failures: 0,
      };
      return { ok: !failed, status: failed ? 500 : 200, json: async () => data };
    },
  });
  vm.runInContext(source, context, { timeout: 1000 });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(registrations, 1, 'Register one click listener when the script starts');
  assert.equal(requests, 1, 'Call main() to load data when the script starts');
  assert.equal(button.disabled, false);
  if (scenario === 'startup_retry') {
    assert.equal(message.textContent, 'cannot read journal or page');
  } else {
    assert.equal(elements.get('title').textContent, 'Initial task');
    assert.equal(elements.get('event-count').textContent, '5');
    assert.equal(elements.get('status').textContent, '\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430');
    assert.equal(elements.get('runs').textContent, '1 / 1');
    assert.equal(message.textContent, '');
  }
  if (scenario !== 'startup_initial') {
    await listener({ type: 'click' });
    assert.equal(requests, 2);
    assert.equal(registrations, 1);
    assert.equal(elements.get('title').textContent, 'Updated task');
    assert.equal(elements.get('event-count').textContent, '6');
    assert.equal(message.textContent, '');
    assert.equal(button.disabled, false);
  }
}

async function check() {
  let { source, scenario, ids } = JSON.parse(fs.readFileSync(0, 'utf8'));
  if (scenario.startsWith('startup_')) {
    await checkStartup(source, scenario, ids);
    return;
  }
  // Function checks isolate the optional final page-startup call.
  source = source.replace(/\r?\n[ \t]*main\s*\(\s*\)\s*;?[ \t]*(?:\r?\n[ \t]*)*$/, '\n');
  if (scenario.startsWith('render_')) {
    checkRender(source, scenario, ids);
    return;
  }
  if (scenario.startsWith('refresh_')) {
    await checkRefresh(source, scenario, ids);
    return;
  }
  if (scenario.startsWith('main_')) {
    checkMain(source, scenario, ids);
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
