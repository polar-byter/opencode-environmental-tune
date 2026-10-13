// Kit Dashboard page. Plain JavaScript, no libraries, no build step, no network beyond
// this server. Charts are inline SVG.
//
// Status: SKELETON. Every function throws until it is implemented (steps 10.x in the
// original architecture, now archived in the vault folder "Дашборд OpenCode").
// Later full interface. The first browser exercise is static/simple.html.
'use strict';

const state = {
  token: null,        // from GET /api/meta, sent as X-Dashboard-Token on every POST
  projects: [],       // GET /api/projects
  selected: null,     // {project, task}
};

async function getJson(url) { throw new Error('TODO step 10.1: getJson'); }

async function postJson(url, body) { throw new Error('TODO step 10.2: postJson'); }

function renderProjects() { throw new Error('TODO step 10.3: renderProjects'); }

async function selectTask(project, task) { throw new Error('TODO step 10.4: selectTask'); }

function renderSummary(view) { throw new Error('TODO step 10.5: renderSummary'); }

function renderGuards(guards) { throw new Error('TODO step 10.6: renderGuards'); }

function renderTimeline(view) { throw new Error('TODO step 10.7: renderTimeline'); }

function renderTokens(sessionsView) { throw new Error('TODO step 10.8: renderTokens'); }

function renderFeed(sessionsView) { throw new Error('TODO step 10.9: renderFeed'); }

function renderSettings(project, settingsView) { throw new Error('TODO step 10.10: renderSettings'); }

function connectStream() { throw new Error('TODO step 10.11: connectStream'); }

async function main() { throw new Error('TODO step 10.12: main'); }

main().catch((error) => {
  document.body.insertAdjacentHTML('afterbegin',
    `<p class="fatal">Dashboard failed to start: ${String(error.message || error)}</p>`);
});
