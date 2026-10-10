// Kit Dashboard page. Plain JavaScript, no libraries, no build step, no network beyond
// this server. Charts are inline SVG.
//
// Status: SKELETON. Every function throws until it is implemented (steps 10.x in the
// vault note "20. Веб-дашборд. План и архитектура").
'use strict';

const state = {
  token: null,        // from GET /api/meta, sent as X-Dashboard-Token on every POST
  projects: [],       // GET /api/projects
  selected: null,     // {project, task}
};

// GET a JSON endpoint; on a non-2xx answer throw Error(body.error || status text).
async function getJson(url) { throw new Error('TODO step 10.1: getJson'); }

// POST JSON with Content-Type application/json and X-Dashboard-Token; same errors as getJson.
async function postJson(url, body) { throw new Error('TODO step 10.2: postJson'); }

// Sidebar: projects with their model choice (Master Chief / executors) and task list with a
// status badge (running / halted / finished). Clicking a task calls selectTask.
function renderProjects() { throw new Error('TODO step 10.3: renderProjects'); }

// Load the task view and its sessions, render every card. Remember the selection in
// location.hash (#<project>/<task>) so a reload keeps it.
async function selectTask(project, task) { throw new Error('TODO step 10.4: selectTask'); }

// Header card: title, status, start/last event time, pieces, reworks, green work runs,
// last full run, halt reason (highlighted) if halted.
function renderSummary(view) { throw new Error('TODO step 10.5: renderSummary'); }

// One horizontal bar per guard: value / limit; amber from 2/3 of the limit, red at the limit.
function renderGuards(guards) { throw new Error('TODO step 10.6: renderGuards'); }

// SVG timeline: x = time from task start; one lane per piece from started_at to accepted_at
// (or now), coloured by state; test runs as dots on a separate lane (green passed, red not
// green, grey baseline). A tooltip (<title>) shows the details.
function renderTimeline(view) { throw new Error('TODO step 10.7: renderTimeline'); }

// Token table and stacked bar per group (paid / local / free / unknown); "нет данных" for null.
function renderTokens(sessionsView) { throw new Error('TODO step 10.8: renderTokens'); }

// Newest-first list of feed rows: time, role, model, tool + target or text. Busy sessions
// ("now") are pinned on top with a running indicator.
function renderFeed(sessionsView) { throw new Error('TODO step 10.9: renderFeed'); }

// Settings form of the selected project: the same fields as the tkinter window, model lists
// with a Refresh button (GET /api/models), Save / Apply / Reset (POST), status line.
// Typed key fields are type="password" and are cleared after a successful save.
function renderSettings(project, settingsView) { throw new Error('TODO step 10.10: renderSettings'); }

// EventSource('/api/stream'): on "change" reload only the affected part (task journal ->
// task view; choice/overlay -> project list and settings). Show online/offline in the topbar.
function connectStream() { throw new Error('TODO step 10.11: connectStream'); }

async function main() { throw new Error('TODO step 10.12: main'); }

main().catch((error) => {
  document.body.insertAdjacentHTML('afterbegin',
    `<p class="fatal">Dashboard failed to start: ${String(error.message || error)}</p>`);
});
