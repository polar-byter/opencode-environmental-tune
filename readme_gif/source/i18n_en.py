"""English strings for the GIF set (GIF_LANG=en). Keys are the Russian source strings.

Configurator labels follow its real English UI (kit/configurator/i18n.py).
The dashboard page itself is Russian; its labels are translated here for readability.
"""

EN = {
    # ---- GIF 1 -------------------------------------------------------
    'требования и критерии приёмки (необязателен)': 'requirements and acceptance criteria (optional)',
    'правила кита, стек, команда тестов': 'kit rules, stack, test command',
    'Obsidian: план, решения, где остановились': 'Obsidian: plan, decisions, where we stopped',
    'как проект устроен сейчас + код': 'how the project is built today + code',
    'перед настройкой моделей и учётом': 'before model setup and task metrics',
    'Мастер Чиф': 'Master Chief',
    'агент build: планирует, пишет каркас и тесты, проверяет': 'build agent: plans, writes skeleton and tests, reviews',
    '«Добавь учёт расходов: сумма, категория, дата. Отрицательную сумму не принимать.»':
        '"Add expense tracking: amount, category, date. Reject negative amounts."',
    'Как Мастер Чиф планирует: документы → решения → каркас и тесты':
        'How the Master Chief plans: documents → decisions → skeleton and tests',
    'Мастер Чиф (агент build) сам находит и читает нужные документы. От пользователя нужна только задача.':
        'The Master Chief (the build agent) finds and reads the documents it needs. You only describe the task.',
    'Задача приходит прямо из чата — или из TASK.md по короткому «Начинай». Текущее сообщение в чате важнее файла.':
        'The task comes straight from chat, or from TASK.md after a short "Start". The current chat message wins over the file.',
    'TASK.md — требования и критерии приёмки, не план реализации. Пустой или старый файл не мешает задаче из чата.':
        'TASK.md holds requirements and acceptance criteria, not an implementation plan. An empty or old file never blocks a chat task.',
    'AGENTS.md — правила кита: порядок работы, стек и команда тестов, где лежит план, что можно поручать исполнителю.':
        'AGENTS.md holds the kit rules: workflow, stack and test command, where the plan lives, what an executor may do.',
    'find_vault.py находит Obsidian Vault → currentsteps.md: что уже сделано, принятые решения и следующий шаг. Это память между сессиями.':
        'find_vault.py locates the Obsidian vault → currentsteps.md: what is done, decisions made, the next step. Memory between sessions.',
    'README, ARCHITECTURE.md и сам код — чтобы новое решение вписалось в существующую архитектуру.':
        'README, ARCHITECTURE.md and the code itself, so the new work fits the existing architecture.',
    'LOCAL_MODELS и METRICS читаются по мере надобности: перед настройкой моделей и перед учётом задачи.':
        'LOCAL_MODELS and METRICS are read when needed: before model setup and before task metrics.',
    'Решения: модули и их интерфейсы, зависимости и порядок, одно задание исполнителю — небольшой класс целиком. План записан в currentsteps.md.':
        'Decisions: modules and interfaces, dependencies and order, one executor job = one small complete class. The plan goes to currentsteps.md.',
    'task_metrics start открывает учёт задачи и сам запускает дашборд. Время и токены этой задачи не смешаются с прошлой работой.':
        'task_metrics start opens task tracking and launches the dashboard. Time and tokens never mix with earlier work.',
    'Каркас: классы, сигнатуры и все импорты, подробная спецификация в каждой функции, а вместо тела — заглушка «TODO: executor».':
        'Skeleton: classes, signatures and every import, a detailed spec in each function, and a "TODO: executor" stub instead of a body.',
    'Тесты пишутся сразу по спецификации. Красный результат ожидаем: один baseline-прогон фиксирует его до начала работы.':
        'Tests are written right away from the spec. Red is expected: one baseline run records it before work starts.',
    'Готово к передаче: требования, план, каркас и красные тесты. Тела функций Мастер Чиф не пишет — их заполняет исполнитель (GIF 2).':
        'Ready to hand off: requirements, plan, skeleton, red tests. The Master Chief never writes bodies; the executor does (GIF 2).',
    'Пользователь': 'You',
    'Решения Мастер Чифа': 'Master Chief decisions',
    'модули и публичные интерфейсы': 'modules and public interfaces',
    'зависимости → порядок модулей': 'dependencies → module order',
    '1 задание = небольшой класс целиком': '1 job = one small complete class',
    'план и решения → currentsteps.md': 'plan and decisions → currentsteps.md',
    'учёт задачи · дашборд открывается сам': 'task tracking · dashboard opens itself',
    'app/expense_service.py — каркас': 'app/expense_service.py — skeleton',
    'baseline: 0 из 3 — ожидаемо красные': 'baseline: 0 of 3 — red, as expected',
    'не пишет тела функций': 'never writes function bodies',
    'или: TASK.md + «Начинай»': 'or: TASK.md + "Start"',
    'план обновлён': 'plan updated',
    '→ дашборд': '→ dashboard',

    # ---- GIF 2 -------------------------------------------------------
    'amount <= 0 → ValueError, раньше всего': 'amount <= 0 → ValueError, checked first',
    'пустая категория → ValueError': 'empty category → ValueError',
    'add возвращает id новой записи': 'add returns the new record id',
    'Мастер Чиф · ревью ExpenseService': 'Master Chief · reviewing ExpenseService',
    'исполнитель · ExpenseService · попытка 2': 'executor · ExpenseService · attempt 2',
    'Мастер Чиф · следующий модуль': 'Master Chief · next module',
    'пример: лимит возвратов исчерпан': 'example: rework limit reached',
    'Дашборд': 'Dashboard',
    '127.0.0.1 · expenses-20261015 · обновление каждые 2 с': '127.0.0.1 · expenses-20261015 · refresh every 2 s',
    'Функции: заявлено / принято': 'Functions: reported / accepted',
    'Сейчас в работе:': 'Working now:',
    'требования, ревью, тесты': 'requirements, review, tests',
    'журнал, снимки, тесты, лимиты': 'journal, snapshots, tests, limits',
    'Исполнитель': 'Executor',
    'LM Studio · OpenRouter · свой API': 'LM Studio · OpenRouter · own API',
    'Передача исполнителю, ревью и дашборд': 'Handing off to the executor, review and the dashboard',
    'Три участника: Мастер Чиф решает и проверяет, исполнитель пишет тела функций, task_metrics.py ведёт журнал. Дашборд показывает всё вживую.':
        'Three roles: the Master Chief decides and reviews, the executor writes bodies, task_metrics.py keeps the journal. The dashboard shows it live.',
    'Перед вызовом требования записываются в .metrics/<ID>/<work_item>-requirements.json: каждый пограничный случай, порядок проверок, инварианты.':
        'Before each call the requirements go to .metrics/<ID>/<work_item>-requirements.json: every edge case, check order, invariant.',
    'Архитектура и реестр функций публикуются в дашборд (dashboard.tracking) — появляется общий счёт функций задачи.':
        'The architecture and function registry are published to the dashboard (dashboard.tracking), so the total function count is known.',
    'delegate замораживает требования и делает снимок хешей всех файлов проекта, включая новые и игнорируемые Git. Выдаётся delegation_id.':
        'delegate freezes the requirements and hashes every project file, including new and Git-ignored ones. It issues a delegation_id.',
    'Исполнитель получает один файл со спецификациями и свой progress-файл. Заполняет только тела функций, отмечая текущую функцию — дашборд видит прогресс.':
        'The executor gets one file with specs plus its own progress file. It fills bodies only and marks the current function, so the dashboard sees progress.',
    'Сразу после ответа — inspect, до любых правок и тестов. Изменён чужой файл → exit 1 и возврат. Здесь границы соблюдены.':
        'Right after the reply: inspect, before any edits or tests. A foreign file changed → exit 1 and rework. Here the boundaries held.',
    'Ревью по каждому требованию: место в коде + тест. Мастер Чиф дописал тест на пустую категорию — он упал. Зелёных тестов недостаточно.':
        'Review per requirement: code location + test. The Master Chief added an empty-category test, and it failed. Green tests are not enough.',
    'review --result rework: один возврат, даже если замечаний несколько. Новая попытка снова регистрируется через delegate.':
        'review --result rework: one rework, however many remarks. The new attempt is registered with delegate again.',
    'Вторая попытка: inspect чист, тесты области зелёные, каждое требование подтверждено → review --result accepted. Функции становятся «принятыми».':
        'Attempt two: inspect is clean, scoped tests are green, every requirement is verified → review --result accepted. Functions become "accepted".',
    'Защита от зацикливания: при срабатывании лимита task_metrics возвращает exit 3 STOP — Мастер Чиф останавливается и ждёт решения пользователя.':
        'Loop guard: when a limit is hit, task_metrics returns exit 3 STOP. The Master Chief stops and waits for your decision.',
    'В конце обязателен полный прогон --scope full, затем finish: отчёт со временем, возвратами, прогонами и токенами по группам моделей.':
        'At the end a full --scope full run is required, then finish: a report with time, reworks, runs and tokens per model group.',
    'выполняется': 'running',
    'STOP · ждёт решения': 'STOP · awaiting decision',
    'итоговый отчёт готов': 'final report ready',
    'Задания исполнителю': 'Executor jobs',
    'Задания приняты': 'Jobs accepted',
    'Возвраты на доработку': 'Reworks',
    'Успешные прогоны / все': 'Green runs / all',
    'реестр не опубликован': 'registry not published',
    'пишет': 'writes',
    'delegate · снимок до вызова': 'delegate · snapshot before the call',
    'вернул': 'returned',
    'Защита от зацикливания → exit 3 STOP': 'Loop guard → exit 3 STOP',
    'одно задание возвращено 3 раза (или 3 сбоя без изменений файлов)': 'the same job sent back 3 times (or 3 failures with no file changes)',
    '3 прогона подряд без читаемого результата (сборка, таймаут, нет тестов)': '3 runs in a row with no readable result (build, timeout, no tests)',
    '12 красных рабочих прогонов подряд в одной области': '12 red work runs in a row in the same scope',
    '60 прогонов с начала задачи или с последнего resume': '60 runs since the start or the last resume',
    'Дальше — только после решения пользователя: task_metrics resume --reason "…"': 'Continue only after your decision: task_metrics resume --reason "…"',
    'исполнитель · ExpenseService · ': 'executor · ExpenseService · ',
    '✓ Работа завершена': '✓ Work complete',
    'требования заморожены': 'requirements frozen',
    'хеши всех файлов проекта': 'hashes of all project files',
    'inspect · что изменила попытка': 'inspect · what the attempt changed',
    'файл + спецификации': 'file + specs',
    'попытка 2 · d-02': 'attempt 2 · d-02',
    'Возвраты': 'Reworks',
    'checks.json — ревью': 'checks.json — review',
    '✓ app/expense_service.py — разрешён': '✓ app/expense_service.py — allowed',
    '✓ tests/ не тронуты': '✓ tests/ untouched',
    '✓ других изменений нет': '✓ no other changes',
    'exit 0 → можно ревьюить': 'exit 0 → ready for review',
    'замечание + delegate': 'remark + delegate',
    'report.md — статистика (пример)': 'report.md — statistics (example)',
    '{a} / {b} из {c}': '{a} / {b} of {c}',
    'checks.json — все verified': 'checks.json — all verified',
    'exit 1 · 2 из 3': 'exit 1 · 2 of 3',
    'Время задачи': 'Task time',
    '18 мин': '18 min',
    'Полные прогоны': 'Full runs',
    '1 из 1': '1 of 1',
    'Токены платных моделей': 'Paid model tokens',
    'Локальные · lmstudio': 'Local · lmstudio',
    'Бесплатные облачные · :free': 'Free cloud · :free',
    'нет данных': 'no data',
    '     код: нет проверки category': '     code: no category check',
    'exit 0 · 3 из 3': 'exit 0 · 3 of 3',
    'полный набор без фильтра': 'whole suite, no filter',
    'exit 0 · все тесты OK': 'exit 0 · all tests OK',
    'нет заданий без ревью': 'no jobs without review',
    '     код: add() · тест: test_': '     code: add() · test: test_',

    # ---- GIF 3 -------------------------------------------------------
    '«Добавь учёт расходов: сумма, категория и дата. Отрицательную сумму принимать нельзя. Сначала покажи план.»':
        '"Add expense tracking: amount, category and date. Negative amounts are not allowed. Show me the plan first."',
    'Кит в проекте': 'Kit in project',
    'Модели и API': 'Models and APIs',
    'Сохранение': 'Saving',
    'Задача': 'Task',
    'Шаблон кита': 'Kit template',
    'Мой проект (любой язык)': 'My project (any language)',
    'В .gitignore проекта:': 'Add to the project .gitignore:',
    'исходный opencode.jsonc с комментариями не переписывается — кит пишет только надстройку':
        'your commented opencode.jsonc is never rewritten; the kit writes only an overlay',
    'результат тестов читается — можно работать': 'test results are readable — ready to work',
    'exit 4 → сначала исправить настройку': 'exit 4 → fix the setup first',
    'Читаемый результат: итог Python unittest или JUnit XML (Maven, Gradle, .NET, Vitest, Jest, Go, Rust, PHPUnit). Таблица команд для разных языков — в README.':
        'Readable result: a Python unittest summary or JUnit XML (Maven, Gradle, .NET, Vitest, Jest, Go, Rust, PHPUnit). Commands per language are in the README.',
    'Локально · LM Studio': 'Local · LM Studio',
    'уже загруженная модель; кит не грузит и не выгружает': 'a model you already loaded; the kit never loads or unloads',
    'Модель из OpenCode': 'Model from OpenCode',
    'подключена через /connect: OpenCode Go, ChatGPT, OpenRouter…': 'connected via /connect: OpenCode Go, ChatGPT, OpenRouter…',
    'Свой API': 'Own API',
    'любой OpenAI-совместимый: адрес …/v1 + ключ + модель': 'any OpenAI-compatible: …/v1 address + key + model',
    'Без файла выбора: Мастер Чиф — из opencode.jsonc, исполнители — загруженная модель LM Studio.':
        'No selection file: the Master Chief uses opencode.jsonc, executors use the loaded LM Studio model.',
    'Модели проекта — OpenCode Kit': 'Project models — OpenCode Kit',
    'Из настроек проекта': 'Project defaults',
    'Модель OpenCode': 'OpenCode model',
    'Получить модели': 'Get models',
    'Подключения, уже известные OpenCode. Полное имя: провайдер/модель.': 'Connections already known to OpenCode. Use the full provider/model ID.',
    '1. Адрес API': '1. API address',
    'Проверить связь': 'Check connection',
    '2. API-ключ': '2. API key',
    '3. Модель': '3. Model',
    'Исполнители': 'Executors',
    'Переменная пользователя Windows': 'Windows user variable',
    'В файле проекта — только имя переменной. Папки с одним именем переменной используют один ключ. Ключ не отправляется в чат.':
        'The project file stores only the variable name. Folders with the same name share one key. Never paste a key into chat.',
    'Способ А · ТЗ в чате': 'Way A · task in chat',
    'Способ Б · TASK.md + «Начинай»': 'Way B · TASK.md + "Start"',
    '«Начинай»': '"Start"',
    'читает требования и сам находит остальное': 'reads the requirements and finds the rest itself',
    'Явное сообщение в чате важнее файла. TASK.md без просьбы не перезаписывается. Открытие папки само по себе работу не запускает.':
        'An explicit chat message wins over the file. TASK.md is never overwritten unless you ask. Opening the folder alone starts nothing.',
    'задача принята': 'task accepted',
    'Настройка проекта под новую задачу': 'Setting up a project for a new task',
    'Новый проект: скопируй в него opencode.jsonc, AGENTS.md, .opencode/commands/ и kit/. Кит не зависит от языка проекта.':
        'New project: copy opencode.jsonc, AGENTS.md, .opencode/commands/ and kit/ into it. The kit works with any language.',
    'В AGENTS.md меняются только разделы «# EDIT»: команда тестов, папки, имя плана. Одна проверка check подтверждает, что результат тестов читается.':
        'In AGENTS.md you edit only the "# EDIT" sections: test command, folders, plan name. One check run confirms test results are readable.',
    'У каждой роли свой источник модели: LM Studio, модель, уже подключённая в OpenCode, или любой OpenAI-совместимый API.':
        'Each role has its own model source: LM Studio, a model already connected in OpenCode, or any OpenAI-compatible API.',
    'Конфигуратор (кнопка «Настройки моделей» в дашборде). Мастер Чиф → «Модель из OpenCode»: подключения, уже известные OpenCode через /connect.':
        'The configurator (the model settings button in the dashboard). Master Chief → "Model from OpenCode": connections OpenCode knows via /connect.',
    'Исполнители → «Свой API»: адрес …/v1, ключ, модель. «Проверить связь» и «Получить модели» ничего не генерируют и не сохраняют.':
        'Executors → "Own API": …/v1 address, key, model. "Check connection" and "Get models" never generate or save anything.',
    '«Сохранить настройки» → .opencode/kit-models.json для этой папки. Сам ключ — в переменной пользователя Windows, не в файле проекта.':
        '"Save settings" → .opencode/kit-models.json for this folder. The key itself lives in a Windows user variable, not in the project.',
    '«Подготовить OpenCode» собирает надстройку .opencode/opencode.jsonc. Текущая сессия не переключается: открой новый чат build (после нового ключа — перезапусти Desktop).':
        '"Prepare OpenCode" builds the .opencode/opencode.jsonc overlay. The current session does not switch: open a new build chat (restart Desktop after a new key).',
    'Поставить задачу можно двумя равными способами: написать ТЗ прямо в чате или заполнить TASK.md и отправить «Начинай».':
        'Two equal ways to give a task: write it straight into chat, or fill in TASK.md and send "Start".',
    'Дальше Мастер Чиф сам читает остальные документы, открывает учёт и дашборд и показывает план — или работает автономно, если ты так разрешил.':
        'Then the Master Chief reads the other documents, opens tracking and the dashboard, and shows the plan, or works on its own if you allowed it.',
    'архитектура, каркас, ревью': 'architecture, skeleton, review',
    'executor и executor-fast — один выбор': 'executor and executor-fast: one choice',
    'Архитектура и ревью': 'Planning & review',
    'Реализация кода': 'Code implementation',
    'Каталог и цены': 'Model catalog & prices',
    'Сохранить настройки': 'Save settings',
    'Подготовить OpenCode': 'Prepare OpenCode',
    'Вернуть по умолчанию': 'Restore defaults',
    'Получено моделей: 3. Выбери модель из списка.': 'Found 3 models. Choose one from the list.',
    'выбор ролей': 'role choices',
    'собирает настройки': 'builds the settings',
    'надстройка поверх исходного конфига': 'overlay on top of the original config',
    'Новый чат build': 'New build chat',
    'после нового ключа — перезапуск Desktop': 'after a new key, restart Desktop',
    '# Домашний бюджет': '# Home budget',
    '- покупки: продукт, кол-во, цена': '- purchases: product, quantity, price',
    '- остатки дома, расходы недели': '- stock at home, weekly spending',
    '## Критерии приёмки': '## Acceptance criteria',
    '- данные сохраняются между запусками': '- data survives restarts',
    'Читает сам': 'Reads on its own',
    'AGENTS.md · currentsteps.md · README · архитектура': 'AGENTS.md · currentsteps.md · README · architecture',
    'учёт задачи + дашборд открывается автоматически': 'task tracking + the dashboard opens automatically',
    'План в currentsteps.md': 'Plan in currentsteps.md',
    'модули, интерфейсы, порядок': 'modules, interfaces, order',
    'Утверждение': 'Approval',
    'показывает план — или идёт дальше, если ты разрешил всю задачу': 'shows the plan, or goes on if you approved the whole task',
    'Нужна сильная модель: архитектура, спецификации, ревью.': 'Use a strong model here: architecture, specs, review.',
    '«Модель из OpenCode» — то, что подключено через /connect: OpenCode Go, подписка ChatGPT, OpenRouter и др.':
        '"Model from OpenCode" is anything connected via /connect: OpenCode Go, a ChatGPT subscription, OpenRouter and more.',
    'Для своего сервиса — вариант «Свой API».': 'For your own service, choose "Own API".',
    'Адрес — базовый, без /chat/completions и /models.': 'Use the base address, without /chat/completions or /models.',
    'Ключ скрыт маской. Если он уже сохранён, окно пишет «Ключ найден» — вводить заново не нужно.':
        'The key is masked. If it is already saved, the window says "Key found" and you need not type it again.',
    '«Проверить связь»: API доступен. Генерация не запускается, ничего не сохраняется.':
        '"Check connection": the API is reachable. No generation runs, nothing is saved.',
    '«Получить модели» заполняет список; имя можно ввести и вручную.': '"Get models" fills the list; you can also type the ID by hand.',

    # ---- GIF 4 -------------------------------------------------------
    'Учёт токенов': 'Token accounting',
    'Загруженные модели': 'Loaded models',
    'или --prepare-only в Desktop': 'or --prepare-only in Desktop',
    'Общий список /v1/models показывает и незагруженные модели. Поле loaded_instances нового API отличает реально загруженные экземпляры — именно их кит и использует.':
        'The plain /v1/models list also shows models that are not loaded. The loaded_instances field of the newer API marks the really loaded ones, and the kit uses those.',
    'Embedding-модели нужны для поиска и векторов, а не для написания кода, поэтому в выбор исполнителя не попадают.':
        'Embedding models serve search and vectors, not code writing, so they are never chosen as executors.',
    'Сколько загружено LLM?': 'How many LLMs are loaded?',
    'Указать незагруженную модель через --model — ошибка: кит не подменяет её другой и не запускает OpenCode.':
        'Passing a model that is not loaded via --model is an error: the kit never swaps in another model and does not start OpenCode.',
    '.opencode/opencode.jsonc  (надстройка, упрощённо)': '.opencode/opencode.jsonc  (overlay, simplified)',
    'Как запускается': 'How to launch',
    '«fast» — это роль, а не другая маленькая модель: оба исполнителя работают на одном загруженном экземпляре. Исходный opencode.jsonc с комментариями не переписывается.':
        '"fast" is a role, not a smaller model: both executors run on the same loaded instance. Your commented opencode.jsonc is never rewritten.',
    'офлайн-проверка цепочки Мастер Чиф → исполнитель': 'offline check of the Master Chief → executor chain',
    'Подставить в:': 'Assign to:',
    'условные данные · реальный каталог: openrouter.ai/api/v1/models': 'sample data · real catalog: openrouter.ai/api/v1/models',
    '«Для кода»': '"For coding"',
    'подборка programming + упоминание кода в описании. Это способ отбора, а не рейтинг качества.':
        'the programming category + code mentioned in the description. A filter, not a quality ranking.',
    'Инструменты': 'Tools',
    'включено по умолчанию: без tool calling агент не работает': 'on by default: an agent cannot work without tool calling',
    'Бесплатные': 'Free models',
    'определяются по опубликованным ставкам; ID оканчивается на :free': 'detected from published rates; the ID ends with :free',
    'черновик роли · Исполнители': 'role draft · Executors',
    'Щелчок ничего не сохраняет и не запускает генерацию.': 'A click saves nothing and runs no generation.',
    'Мастер Чиф выбирается так же —': 'The Master Chief is chosen the same way:',
    'другой ролью в «Подставить в:».': 'pick the other role in "Assign to:".',
    'Модели проекта — OpenCode Kit · Исполнители': 'Project models — OpenCode Kit · Executors',
    '✓ Ключ найден': '✓ Key found',
    'OPENROUTER_API_KEY · повторно вводить не нужно': 'OPENROUTER_API_KEY · no need to enter it again',
    '2. Заменить API-ключ (необязательно)': '2. Replace API key (optional)',
    'будет использован сохранённый ключ': 'Saved key will be used',
    'Связь установлена. OpenRouter принял ключ.': 'Connected. OpenRouter accepted the key.',
    'Генерация модели и инструменты не проверялись.': 'Model generation and tools were not tested.',
    'Ключ — в Windows': 'The key lives in Windows',
    'переменная пользователя; в kit-models.json только её имя': 'a user variable; kit-models.json stores only its name',
    'Один ключ на две роли': 'One key for both roles',
    'OPENROUTER_API_KEY подходит и Мастер Чифу, и исполнителям': 'OPENROUTER_API_KEY serves both the Master Chief and the executors',
    'Новый ключ?': 'New key?',
    'полностью перезапусти Desktop, чтобы он увидел новое окружение': 'fully restart Desktop so it sees the new environment',
    'модели OpenRouter доступны OpenCode': 'OpenRouter models are now available to OpenCode',
    'Счётчики берутся из экспорта сессий OpenCode (основной и дочерних) за время задачи. Денежную стоимость скрипт не считает; недостающие данные остаются «неизвестно».':
        'Counters come from the OpenCode session export (main and child sessions) during the task. No money cost is computed; missing data stays "unknown".',
    'Модели: LM Studio и OpenRouter': 'Models: LM Studio and OpenRouter',
    'LM Studio: ты сам загружаешь модель (контекст, GPU и прочие параметры) и включаешь сервер. Кит использует эту загрузку и никогда не вызывает Load/Unload.':
        'LM Studio: you load the model yourself (context, GPU and other settings) and turn on the server. The kit uses it and never calls Load/Unload.',
    'run_opencode.py читает /api/v1/models: поле loaded_instances показывает реально загруженные экземпляры. Embedding-модели пропускаются.':
        'run_opencode.py reads /api/v1/models: the loaded_instances field shows the really loaded instances. Embedding models are skipped.',
    'Одна загруженная LLM — используется она. Несколько — та, что выбрана в настройках, иначе кит покажет ID и попросит выбрать. Ни одной — попросит загрузить.':
        'One loaded LLM: it is used. Several: the one chosen in settings, otherwise the kit lists IDs and asks. None: it asks you to load one.',
    'Выбор пишется в надстройку .opencode/opencode.jsonc: executor и executor-fast получают один загруженный экземпляр. Мастер Чиф и права не меняются.':
        'The choice goes to the .opencode/opencode.jsonc overlay: executor and executor-fast share one loaded instance. The Master Chief and permissions stay as they are.',
    'check_env.py проверяет конфиг, связь с LM Studio и короткий пробный ответ. Сменил модель в LM Studio — запусти подготовку заново.':
        'check_env.py checks the config, the LM Studio connection and a short probe reply. Changed the model in LM Studio? Prepare again.',
    'OpenRouter: в конфигураторе раздел «OpenRouter — Каталог и цены». Публичный каталог грузится без ключа; цены — USD за 1 млн токенов, вход и выход отдельно.':
        'OpenRouter: the configurator tab "OpenRouter — Model catalog & prices". The public catalog loads without a key; prices are USD per 1M tokens, input and output.',
    'Фильтры: «Для кода», «Только с инструментами» (агентам они нужны) и «Бесплатные». Таблица ниже — условные данные для примера.':
        'Filters: "For coding", "Tool support only" (agents need tools) and "Free models". The table shows sample data.',
    'Выбери роль в «Подставить в:» и щёлкни строку: роль получает «Свой API», адрес https://openrouter.ai/api/v1 и точный ID модели с окончанием :free.':
        'Pick a role in "Assign to:" and click a row: the role gets "Own API", https://openrouter.ai/api/v1 and the exact model ID ending in :free.',
    '«К настройкам роли»: сохранённый ключ OPENROUTER_API_KEY виден как «Ключ найден». «Проверить связь» → OpenRouter принял ключ. Затем сохранить и подготовить.':
        '"Role settings": a saved OPENROUTER_API_KEY shows as "Key found". "Check connection" → OpenRouter accepted the key. Then save and prepare.',
    'Другой путь: подключить OpenRouter в OpenCode через /connect и выбрать «Модель из OpenCode», например openrouter/…:free. LM Studio тогда не опрашивается.':
        'Another way: connect OpenRouter in OpenCode via /connect and pick "Model from OpenCode", e.g. openrouter/…:free. LM Studio is then not queried.',
    'В отчёте токены делятся на группы: lmstudio — локальные, OpenRouter «:free» — бесплатные облачные, остальные — платные. Нет данных — «неизвестно», а не ноль.':
        'The report groups tokens: lmstudio = local, OpenRouter ":free" = free cloud, everything else = paid. No data means "unknown", never zero.',
    'Модель и её параметры выбираешь ты': 'You choose the model and its settings',
    'размер контекста, распределение по GPU и др.': 'context size, GPU offload and so on',
    'Кит не вызывает Load / Unload': 'The kit never calls Load / Unload',
    'и не отправляет параметры загрузки': 'and never sends load parameters',
    'Не выгружай модель во время задачи': 'Do not unload the model during a task',
    'выбор делается до запуска, а не перед каждым токеном': 'the choice is made before launch, not per token',
    'одна': 'one',
    'используется она — даже если в конфиге указана другая': 'it is used, even if the config names another one',
    'несколько': 'several',
    'выбранная в настройках (executor / instance); если неоднозначно — кит показывает ID: run_opencode.py --model "ID"':
        'the one chosen in settings (executor / instance); if unclear, the kit lists IDs: run_opencode.py --model "ID"',
    'ни одной': 'none',
    'кит просит загрузить модель в LM Studio и ничего не запускает': 'the kit asks you to load a model in LM Studio and starts nothing',
    'OpenCode Desktop уже открыт': 'OpenCode Desktop is already open',
    'Из терминала': 'From a terminal',
    'py kit/run_opencode.py  (свой сервер, переменные OPENCODE_KIT_*)': 'py kit/run_opencode.py  (private server, OPENCODE_KIT_* variables)',
    'Для кода': 'For coding',
    'Только с инструментами': 'Tool support only',
    'Модель · API ID': 'Model · API ID',
    'Контекст': 'Context',
    'Вход $/1M': 'Input $/1M',
    'Выход $/1M': 'Output $/1M',
    'Каталог без ключа': 'Catalog without a key',
    'грузится при открытии раздела; кэш — .metrics/.openrouter-catalog.json': 'loads when the tab opens; cache in .metrics/.openrouter-catalog.json',
    'Цены каталога': 'Catalog prices',
    'USD за 1 млн токенов: вход и выход отдельно; «—» — цена неизвестна': 'USD per 1M tokens, input and output separately; "—" means unknown',
    '«Обновить цены»': '"Refresh prices"',
    'без интернета показан прежний каталог с пометкой давности': 'offline, the previous catalog is shown with its age',
    'Источник': 'Source',
    'Адрес API': 'API address',
    'Модель': 'Model',
    'локально, без оплаты API; модель загружена у тебя': 'local, no API fees; the model runs on your machine',
    'OpenRouter через /connect': 'OpenRouter via /connect',
    'ключ хранит OpenCode': 'OpenCode stores the key',
    'OpenRouter как свой API': 'OpenRouter as own API',
    'ключ — переменная Windows (OPENROUTER_API_KEY)': 'key in a Windows variable (OPENROUTER_API_KEY)',
    'Локальные / бесплатные': 'Local / free',
    'все модели провайдера lmstudio': 'every model of the lmstudio provider',
    'исполнитель на LM Studio': 'executor on LM Studio',
    'Бесплатные облачные': 'Free cloud',
    'модели OpenRouter с окончанием :free': 'OpenRouter models ending in :free',
    'исполнитель …:free': 'executor …:free',
    'Платные': 'Paid',
    'все остальные известные провайдеры': 'every other known provider',
    'обычно Мастер Чиф': 'usually the Master Chief',
    'пример:': 'example:',
    'вход · выход · рассуждения · кэш': 'input · output · reasoning · cache',
    'считаются отдельно': 'are counted separately',
    'пропущена': 'skipped',
    'Исполнители  ▾': 'Executors  ▾',
    'Да': 'Yes',
    'Нет': 'No',
    'выбрана': 'selected',

    # ---- GIF 5 -------------------------------------------------------
    '⏸ Приостановить': '⏸ Pause',
    '▶ Продолжить': '▶ Resume',
    '■ Остановить': '■ Stop',
    'Удалить задачу…': 'Delete task…',
    'Посмотреть архитектуру кода →': 'View code architecture →',
    'Посмотреть детализацию работ →': 'View work details →',
    'Последние события': 'Latest events',
    'Сообщения и действия моделей: публичные ответы и инструменты, без shell и рассуждений':
        'Model messages and actions: public replies and tools, no shell output or reasoning',
    'Категории не складываются в общий расход; денежная стоимость не вычисляется.':
        'Categories are not summed into one total; no money cost is computed.',
    'Семья сессий задачи · общий сервер Desktop': 'Task session family · shared Desktop server',
    'OpenCode · наблюдение за задачей': 'OpenCode · task monitor',
    'Автообновление каждые 2 секунды': 'Auto-refresh every 2 seconds',
    'Настройки моделей': 'Model settings',
    'В работе: 1': 'Running: 1',
    'Как управлять дашбордом': 'Using the dashboard',
    'Дашборд открывается сам: task_metrics start запускает локальный сервер (127.0.0.1) и открывает страницу задачи. Команд вводить не нужно.':
        'The dashboard opens itself: task_metrics start launches a local server (127.0.0.1) and opens the task page. No commands to type.',
    '«Обзор»: статус, возвраты, прогоны тестов, сбои исполнителя и последние события. Страница обновляется каждые 2 секунды.':
        '"Overview": status, reworks, test runs, executor failures and latest events. The page refreshes every 2 seconds.',
    '«Сейчас в работе»: модель, задание, текущая функция, принятые задания, токены и время. Устаревшая отметка функции скрывается через 90 секунд.':
        '"Working now": model, job, current function, accepted jobs, tokens and time. A stale function mark hides after 90 seconds.',
    '«Детализация работ»: каждое задание исполнителю — попытки, файлы, тесты, ревью и публичные действия моделей.':
        '"Work details": every executor job with its attempts, files, tests, reviews and public model actions.',
    '«Токены»: вход, выход, рассуждения и кэш по моделям и ролям. Неизвестное остаётся неизвестным и не заменяется нулём.':
        '"Tokens": input, output, reasoning and cache per model and role. Unknown stays unknown and is never shown as zero.',
    '«Настройки моделей» открывает конфигуратор этого проекта. Ничего не сохраняется и не применяется автоматически — выбор действует для следующей задачи.':
        '"Model settings" opens this project\'s configurator. Nothing is saved or applied automatically; the choice applies to the next task.',
    '«Приостановить» прерывает основную сессию и всех её исполнителей. Пока идёт операция, виден переходный статус.':
        '"Pause" interrupts the main session and all its executors. While it works, a transition status is shown.',
    'Пауза: код, план, история и очередь сообщений сохранены. Новые delegate, test, review и finish этой задачи заблокированы.':
        'Paused: code, plan, history and the message queue are kept. New delegate, test, review and finish calls for this task are blocked.',
    '«Продолжить» отправляет в ту же основную сессию просьбу продолжить тот же task ID и проверить частичные правки. Защитные лимиты не сбрасываются.':
        '"Resume" asks the same main session to continue the same task ID and check partial edits. Loop guards are not reset.',
    '«Остановить» прерывает всю семью сессий и очищает их очереди. Отмена — это не успешное завершение задачи.':
        '"Stop" interrupts the whole session family and clears their queues. A cancel is not a successful finish.',
    '«Удалить задачу…» — после подтверждения: остановка, затем удаление сессий и метрик этой задачи. Исходники приложения остаются.':
        '"Delete task…" after confirmation: stop, then delete this task\'s sessions and metrics. Your application source stays.',
    'После finish вместо «Сейчас в работе» — итог: время, полный прогон, ссылка на папку проекта, файл запуска и итоговый отчёт.':
        'After finish, "Working now" becomes the summary: time, full run, project folder, launch file and the final report.',
    'пауза': 'paused',
    'Обзор': 'Overview',
    'Детализация работ': 'Work details',
    'Токены': 'Tokens',
    'Время 41 мин · полный прогон: 128 тестов, OK': 'Time 41 min · full run: 128 tests, OK',
    'Сейчас в работе': 'Working now',
    'исполнитель · qwen3.8-max': 'executor · qwen3.8-max',
    'Задание': 'Job',
    'Функция': 'Function',
    'Функции реализованы': 'Functions done',
    'Токены: вход / выход': 'Tokens: in / out',
    'С начала задачи': 'Since start',
    'Статус': 'Status',
    'Сбои исполнителя': 'Executor failures',
    'Попытки': 'Attempts',
    'Файл': 'File',
    'Тесты': 'Tests',
    'Ревью': 'Review',
    'Функции': 'Functions',
    'принято': 'accepted',
    'ждёт ревью': 'awaiting review',
    'Модель / роль': 'Model / role',
    'Вход': 'Input',
    'Выход': 'Output',
    'Рассуждения': 'Reasoning',
    'Кэш: чтение': 'Cache read',
    'Кэш: запись': 'Cache write',
    'openai/gpt-6.1-sol · Мастер Чиф': 'openai/gpt-6.1-sol · Master Chief',
    'qwen3.8-max · исполнитель': 'qwen3.8-max · executor',
    'неизвестно': 'unknown',
    'build · Мастер Чиф': 'build · Master Chief',
    'executor · попытка d-07': 'executor · attempt d-07',
    'executor-fast · правка': 'executor-fast · edit',
    'приостанавливается…': 'pausing…',
    'Сессии и метрики задачи удалены. Исходники приложения на месте.': 'Task sessions and metrics deleted. Application source is intact.',
    'Сохранить и подготовить — отдельными кнопками': 'Save and Prepare are separate buttons',
    'delegate · test · review · finish — заблокированы': 'delegate · test · review · finish — blocked',
    'Запрос в ту же основную сессию': 'Message to the same main session',
    'Продолжи задачу expenses-20261015: прочитай план и проверь частичные изменения незавершённой попытки.':
        'Continue task expenses-20261015: read the plan and check the partial edits of the unfinished attempt.',
    'Генерация не продолжается «с того же токена» — Мастер Чиф продолжает по плану. Защитные лимиты сохраняются.':
        'Generation does not resume "from the same token"; the Master Chief continues from the plan. Loop guards stay.',
    'Удалить задачу expenses-20261015?': 'Delete task expenses-20261015?',
    'Сначала будет подтверждена остановка, затем удалятся сессии и метрики этой задачи. Исходники приложения останутся.':
        'The stop is confirmed first, then this task\'s sessions and metrics are deleted. Your application source stays.',
    'Отмена': 'Cancel',
    'Удалить': 'Delete',
    'продолжается…': 'resuming…',
    'останавливается…': 'stopping…',
    'отменена': 'cancelled',
    'удаление…': 'deleting…',
    'удалена': 'deleted',
    'Открыть итоговый отчёт': 'Open final report',
    'Посмотреть файл запуска': 'View launch file',
    'Открыть папку проекта': 'Open project folder',
    ' · пауза': ' · paused',
    '⏸ прервана': '⏸ interrupted',
    'работает': 'working',
    'qwen3.8-max · свой API': 'qwen3.8-max · own API',
    'каталог и цены': 'catalog and prices',
    'Открыть итог': 'Open final',
    '■ очередь очищена': '■ queue cleared',
    'продолжает': 'continuing',
}
