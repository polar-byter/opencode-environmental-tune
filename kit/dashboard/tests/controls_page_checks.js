// Exercise the actual page handlers with deterministic responses and task switches.
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const elements = new Map(input.ids.map(id => [id, {
  textContent: '', hidden: false, disabled: false, value: '', className: '',
  replaceChildren() {}, add() {}, addEventListener() {}, querySelectorAll() { return []; }
}]));
const context = {
  document: {getElementById: id => {assert(elements.has(id), id); return elements.get(id);}},
  window: {location: {search:'?task=first'}, history: {replaceState() {}}, confirm: () => true},
  URLSearchParams, Option: function() {}, setInterval() {}, console,
  KitLocalization: require('../static/localization.js'),
  refreshCount: 0, requests: []
};
vm.createContext(context);
vm.runInContext(input.source.replace(/\s*main\(\);\s*$/, ''), context);
const run = code => vm.runInContext(code, context);
(async () => {
  run(`renderControls({task:'first',session:'ses_root',status:'paused'});`);
  assert.equal(elements.get('resume-task').disabled, false);
  assert.equal(elements.get('pause-task').disabled, true);
  run(`renderControls({task:'first',session:'ses_root',status:'running'});`);
  assert.equal(elements.get('pause-task').disabled, false);
  run(`renderControls({task:'first',session:'ses_root',status:'pausing'});`);
  for (const action of ['pause','resume','cancel','delete']) assert(elements.get(action+'-task').disabled);
  run(`renderControls({task:'first',status:'running'});`);
  assert(elements.get('pause-task').disabled);
  context.fetch = async (url, options) => {
    context.requests.push({url, options});
    return {ok:true,json:async()=>url==='/api/ui'?{token:'ui-token'}:{status:'pausing'}};
  };
  const refresh = run('refreshTask');
  run(`refreshTask=async()=>{refreshCount++};renderControls({task:'first',session:'ses_root',status:'running'});`);
  await run(`controlTask('pause')`);
  const posted = context.requests.find(request=>request.options?.method==='POST');
  assert.equal(posted.url,'/api/task/control');
  assert.deepEqual(JSON.parse(posted.options.body),{task:'first',action:'pause'});
  assert.equal(posted.options.headers['X-Dashboard-UI-Token'],'ui-token');
  context.requests=[];context.window.confirm=()=>false;
  await run(`controlTask('delete')`);
  assert.equal(context.requests.length,0);
  context.window.confirm=()=>true;
  context.fetch=async url=>({ok:url==='/api/ui',statusText:'Failed',json:async()=>url==='/api/ui'?{token:'ui-token'}:{error:'Not confirmed'}});
  await run(`controlTask('cancel')`);
  assert.equal(elements.get('control-message').textContent,'Not confirmed');
  run('renderControls(selectedData)');
  assert.equal(elements.get('control-message').textContent,'Not confirmed');
  let release;
  context.fetch=async url=>url==='/api/ui'?{ok:true,json:async()=>({token:'ui-token'})}:
    new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({status:'cancelled'})});});
  const pending=run(`controlTask('cancel')`);
  await new Promise(resolve=>setImmediate(resolve));
  run(`activeTask='second';controlFailure='';renderControls({task:'second',session:'ses_second',status:'running'});`);
  release();await pending;
  assert.equal(run('selectedData.task'),'second');
  assert.equal(elements.get('control-message').textContent,'');
  context.fetch=async url=>({ok:true,json:async()=>url==='/api/health'?{project:{id:'project',name:'test'}}:
    url==='/api/tasks'?[]:{status:'deleted',message:'Deleted'}});
  context.originalRefresh=refresh;
  run(`refreshTask=originalRefresh;activeTask='first';controlFailure='';`);
  elements.get('models').textContent='old model';elements.get('architecture').hidden=false;
  await run('refreshTask()');
  assert.equal(run('activeTask'),'');
  assert.equal(elements.get('models').textContent,'');
  assert(elements.get('architecture').hidden);
  assert.equal(elements.get('title').textContent,'No tasks yet');
  console.log('Page controls: requests, confirmation, failures, stale replies, empty state OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
