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

// ПОЗЖЕ, после simple.html. getJson(url) -> объект данных из GET-ответа.
// 1. await fetch(url) даёт response; await response.json() даёт data.
// 2. Неуспешный response.ok -> Error(data.error || response.statusText).
// 3. Успех -> верни data. Например '/api/meta' -> {token: ..., projects: [...]}.
// Сетевой сбой не скрывай: вызывающая функция покажет его пользователю.
async function getJson(url) { throw new Error('TODO step 10.1: getJson'); }

// ПОЗЖЕ, этап записи настроек; сначала должен работать getJson.
// url - адрес, body - объект формы. fetch получает method='POST', JSON.stringify(body),
// Content-Type application/json и X-Dashboard-Token из state.token.
// Разбери ответ и ошибки так же, как в getJson. Без токена сервер вернёт отказ.
// Например сохранение -> объект {saved: ..., keys: [...]}; ключи - имена, не секреты.
async function postJson(url, body) { throw new Error('TODO step 10.2: postJson'); }

// ПОЗЖЕ, этап проектов. state.projects содержит данные GET /api/projects.
// Начни с одного проекта и его имени в sidebar; затем циклом добавь его задачи.
// Для задачи покажи title/status, при клике вызови selectTask(project.key, task.id).
// Добавь выбранные модели проекта отдельным подшагом. Пустой список - без задач.
// Создавай DOM-элементы и textContent; не вставляй имена из журнала как HTML.
function renderProjects() { throw new Error('TODO step 10.3: renderProjects'); }

// ПОЗЖЕ, после getJson и первых функций отображения.
// Вход: ключ проекта и id задачи; результат - выбранная задача на странице.
// 1. Сохрани пару в state.selected, загрузи её task view, затем sessions через getJson.
// 2. Передай полученные объекты renderSummary/renderGuards/renderTimeline,
//    renderTokens/renderFeed. Подключай эти представления по мере готовности.
// 3. Запиши '#<project>/<task>' в location.hash: после перезагрузки main восстановит выбор.
// При неудачной загрузке покажи ошибку; не оставляй данные прежней задачи под новым именем.
async function selectTask(project, task) { throw new Error('TODO step 10.4: selectTask'); }

// ПОЗЖЕ. view - ответ task_view; нужные поля находятся в view.summary.
// Начни с title/status через textContent, затем даты и счётчики work_item_count,
// reworks, green_work_runs/work_runs. finished -> время завершения; halted -> halt_reason.
// last_full=null означает «полного рабочего прогона ещё нет», не «всё успешно».
// Предварительно посмотрим пример JSON, чтобы не путать view и view.summary.
function renderSummary(view) { throw new Error('TODO step 10.5: renderSummary'); }

// ПОЗЖЕ, после готовой guard_status. guards - список {name, value, limit, detail}.
// Пример value=2, limit=3 -> полоса заполнена на 2/3.
// Сначала покажи подпись и числа циклом, затем добавь ширину полосы value/limit.
// От 2/3 - жёлтый, на лимите - красный. Полосу ограничивай шириной контейнера;
// текст реального счётчика не обрезай. [] -> нет полос.
function renderGuards(guards) { throw new Error('TODO step 10.6: renderGuards'); }

// ПОЗЖЕ, дополнительный подшаг ПОСЛЕ обычной таблицы заданий, не вместо неё.
// view.work_items - строки заданий, view.tests - запуски тестов.
// Сначала на одном задании переведи время в координату x относительно started_at.
// Затем добавь по дорожке на задание: от started_at до accepted_at либо текущего времени.
// Цвет - state; отдельная дорожка тестов: passed зелёный, остальные красные,
// baseline серый. Подробности в SVG <title>. Нет событий -> пустое состояние, не деление на 0.
// Перед этапом разберём SVG-координаты и пример двух заданий; сейчас график не писать.
function renderTimeline(view) { throw new Error('TODO step 10.7: renderTimeline'); }

// ПОЗЖЕ, после sessions.task_sessions. sessionsView.available=false -> покажи reason.
// Иначе groups содержит paid/local/free/unknown: сначала таблица по этим четырём группам.
// Известные числа показывай как числа, null - 'нет данных', НЕ 0.
// Пример input=10/output=null -> '10' / 'нет данных'. Полосы расхода добавь после таблицы.
function renderTokens(sessionsView) { throw new Error('TODO step 10.8: renderTokens'); }

// ПОЗЖЕ, после готового sessionsView.feed: список строк с at/role/model/kind.
// Начни с текста одной строки; затем список НОВЫХ первыми (данные feed идут старые первыми).
// kind='text' -> text; kind='tool' -> tool и target. Используй textContent.
// sessionsView.now содержит занятые сессии: их текущие действия вынеси сверху.
// Нет доступных сессий -> сообщение reason; пустая feed -> нет действий, не ошибка.
function renderFeed(sessionsView) { throw new Error('TODO step 10.9: renderFeed'); }

// ПОЗЖЕ, только после защиты POST. project - выбранный проект, settingsView - ответ формы.
// 1. Заполни поля из settingsView.form; маски ключей - из settingsView.keys.
// 2. Списки моделей обновляй через GET /api/models; Save/Apply/Reset - через postJson.
// 3. Покажи результат или ошибку рядом с формой. Нельзя показывать исходные ключи.
// Введённые секреты: input type='password', после успешного сохранения очистить.
// Начнём с чтения формы без кнопок записи, затем добавим по одному действию.
function renderSettings(project, settingsView) { throw new Error('TODO step 10.10: renderSettings'); }

// ПОЗЖЕ, необязательное SSE. Ручная кнопка обновления уже должна работать.
// EventSource('/api/stream') держит соединение; change несёт JSON project/name.
// 1. Начни с показа online/offline при соединении/ошибке.
// 2. 'task:<id>' -> обнови эту задачу, если она выбрана;
//    choice/overlay -> перечитай список проектов и настройки.
// Не создавай новое соединение при каждом клике. Перед этапом разберём подписку и закрытие.
function connectStream() { throw new Error('TODO step 10.11: connectStream'); }

// ПОЗЖЕ, после готовых GET и представлений. main связывает запуск полной страницы.
// 1. GET /api/meta -> state.token; GET /api/projects -> state.projects.
// 2. Покажи список проектов. Прочитай location.hash: сохранённую допустимую пару
//    передай selectTask. Нет задач -> пустое состояние, не обращение к tasks[0].
// 3. Подключай настройки и connectStream лишь после их реализации.
// Ошибка старта должна попасть в существующий main().catch ниже.
async function main() { throw new Error('TODO step 10.12: main'); }

main().catch((error) => {
  document.body.insertAdjacentHTML('afterbegin',
    `<p class="fatal">Dashboard failed to start: ${String(error.message || error)}</p>`);
});
