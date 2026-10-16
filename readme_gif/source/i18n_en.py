"""English strings for the GIF set (GIF_LANG=en). Keys are the Russian source strings.

Dashboard, installer and configurator labels follow their real English UI
(kit/locales/ru.json keys and kit/configurator/i18n.py).
"""

EN = {
    # ---- GIF 1: installation ------------------------------------------
    'Создай локальное приложение для домашних дел: список дел с датами и статусами, данные в SQLite. '
    'Следуй правилам кита и выполни весь план.':
        'Create a local to-do application: tasks with due dates and statuses, data in SQLite. '
        'Follow the kit rules and complete the whole plan.',
    'Установка за четыре шага': 'Installation in four steps',
    '✓ Desktop найден': '✓ Desktop found',
    '2. Папка проекта': '2. Project folder',
    '3. Установите кит и выберите модели': '3. Install the kit and choose models',
    'Создать проект и настроить модели': 'Create project and configure models',
    '4. Ваша первая задача': '4. Your first task',
    'Копировать задание': 'Copy prompt',
    'Создание проекта — OpenCode Kit': 'Project setup — OpenCode Kit',
    'Создайте проект OpenCode': 'Create your OpenCode project',
    'Отправить': 'Send',
    'задание отправляешь ты сам —': 'you send the prompt yourself —',
    'мастер ничего не шлёт модели': 'the wizard never sends it to a model',
    'Нужны три вещи: OpenCode Desktop, Python 3.13 с Tk и архив кита с GitHub. Дальше — двойной щелчок по install.cmd.':
        'You need three things: OpenCode Desktop, Python 3.13 with Tk and the kit ZIP from GitHub. '
        'Then double-click install.cmd.',
    'Шаг 1. Мастер сам находит OpenCode Desktop. Если его нет — кнопка «Скачать OpenCode».':
        'Step 1. The wizard finds OpenCode Desktop itself. Missing? Click "Download OpenCode".',
    'Шаг 2. Выбери папку для своего приложения. Если её нет, мастер создаст её сам.':
        'Step 2. Choose a folder for your application. If it does not exist, the wizard creates it.',
    'Шаг 3. Мастер копирует кит в папку проекта и открывает окно настроек моделей.':
        'Step 3. The wizard copies the kit into the project folder and opens the model settings.',
    'Три роли уже заполнены бесплатными моделями. Нажми «Сохранить настройки», затем «Подготовить OpenCode».':
        'All three roles come pre-filled with free models. Click "Save settings", then "Prepare OpenCode".',
    'Шаг 4. Проект открывается в Desktop. Скопируй пример задания, вставь в новый чат build и отправь.':
        'Step 4. The project opens in Desktop. Copy the example prompt, paste it into a new build chat and send.',
    'двойной щелчок — откроется мастер': 'double-click — the setup wizard opens',
    'Модели проекта — OpenCode Kit': 'Project models — OpenCode Kit',
    'Сохранить настройки': 'Save settings',
    'Подготовить OpenCode': 'Prepare OpenCode',
    '✓ настройки подготовлены': '✓ settings prepared',
    'Модель недоступна?': 'Model unavailable?',
    'выбери другую в этом же окне': 'pick another one in the same window',
    'Ключ API': 'API key',
    'хранится в Windows, не в проекте': 'stored in Windows, not in the project',
    'приложение, где работают агенты': 'the app where the agents work',
    'для скриптов и окон кита': 'for the kit scripts and windows',
    'ZIP кита с GitHub': 'Kit ZIP from GitHub',
    'распаковать в отдельную папку': 'unzip into a separate folder',
    'Скопировано в проект:': 'Copied into the project:',
    'МЧ': 'MC',
    'Мастер Чиф': 'Master Chief',
    'И': 'E',
    'Исполнители': 'Executors',
    'MiMo V2.6 Flash Free · 1 одновременно': 'MiMo V2.6 Flash Free · 1 at a time',
    'БФ': 'BF',
    'Исправитель ошибок': 'Bug Fixer',
    '→ открывается окно настроек': '→ the settings window opens',
    'Нет Desktop?': 'No Desktop?',
    'кнопка «Скачать OpenCode», потом «Проверить ещё раз»': '"Download OpenCode", then "Check again"',
    'Своя папка': 'Your own folder',
    'лучше отдельная, вне скачанного кита': 'preferably separate, outside the downloaded kit',
    '✓ кит установлен': '✓ kit installed',

    # ---- GIF 2: team ---------------------------------------------------
    'Кто в команде': 'Who is in the team',
    'Ты': 'You',
    'Я': 'Me',
    'задача и решения': 'task and decisions',
    'план, договорённости, тесты, проверка': 'plan, contracts, tests, review',
    'Журнал и дашборд': 'Journal and dashboard',
    'каждый шаг записан и виден': 'every step recorded and visible',
    'Ты описываешь задачу. Мастер Чиф — главный: строит план, договорённости между частями, тесты и проверяет результат.':
        'You describe the task. The Master Chief leads: plans the work, agrees the contracts between parts, '
        'writes tests and reviews the result.',
    'Исполнители пишут код по готовым описаниям. Их может быть несколько — каждый работает в своей копии файлов.':
        'Executors write code from ready descriptions. There can be several — each works in its own copy of the files.',
    'Исправитель ошибок делает одну попытку, если исполнитель ошибся или упёрся в лимит.':
        'The Bug Fixer gets one attempt if an executor made a mistake or hit a limit.',
    'Контроллер — обычная программа, не ИИ: раздаёт копии файлов, следит за лимитами и переносит принятый код в проект.':
        'The controller is a plain program, not AI: it hands out file copies, watches the limits '
        'and moves accepted code into the project.',
    'Каждый шаг записывается в журнал, а дашборд в браузере показывает, кто чем занят.':
        'Every step goes into the journal, and the browser dashboard shows who is working on what.',
    'В конце Мастер Чиф проверяет интерфейс приложения и после этого завершает задачу.':
        'At the end the Master Chief checks the application interface and then finishes the task.',
    '1–8 одновременно, у каждого своя копия': '1–8 at once, each with its own copy',
    'одна попытка, если исполнитель не справился': 'one attempt if an executor failed',
    'Контроллер': 'Controller',
    'программа: копии файлов, лимиты, перенос в проект': 'a program: file copies, limits, integration',
    'финальная проверка UX/UI': 'final UX/UI review',

    # ---- GIF 3: planning -----------------------------------------------
    'Задача': 'Task',
    'Чтение': 'Reading',
    'Решения': 'Decisions',
    'Заготовки': 'Skeleton',
    'Тесты': 'Tests',
    'Старт': 'Start',
    'Как Мастер Чиф готовит работу': 'How the Master Chief prepares the work',
    'Задачу можно написать прямо в чате — или в файле TASK.md и отправить «Начинай». Если они расходятся, главнее чат.':
        'Write the task straight into chat, or put it in TASK.md and send "Start". If they disagree, chat wins.',
    'Мастер Чиф сам читает нужное: правила кита, план прошлых сессий и то, что уже есть в проекте.':
        'The Master Chief reads what it needs: the kit rules, the plan from earlier sessions and the existing project.',
    'Решает, из каких частей будет программа и в каком порядке. Заранее фиксирует договорённости между частями.':
        'It decides which parts the program needs and in what order, and fixes the contracts between parts up front.',
    'Пишет заготовки: названия функций и подробное описание, что каждая делает. Внутри — пометка «TODO: executor».':
        'It writes blanks: function names and a detailed description of each. Inside — a "TODO: executor" marker.',
    'Сразу пишет тесты. Пока функции пустые, тесты не проходят.':
        'It writes the tests right away. While the functions are empty, the tests fail.',
    'Открывает учёт задачи — дашборд запускается сам. План записан в currentsteps.md.':
        'It opens task tracking — the dashboard starts by itself. The plan is saved in currentsteps.md.',
    'В чате': 'In chat',
    '«Сделай домашний бюджет: покупки по продуктам, остатки дома и расходы за неделю. Сначала покажи план.»':
        '"Build a home budget: purchases by product, stock at home and weekly spending. Show me the plan first."',
    'или': 'or',
    '«Начинай»': '"Start"',
    'перечислять документы не нужно — он находит их сам': 'no need to list documents — it finds them itself',
    '# Домашний бюджет': '# Home budget',
    '- покупки, остатки, расходы': '- purchases, stock, spending',
    '## Критерии приёмки': '## Acceptance criteria',
    '- данные не теряются': '- data is never lost',
    'правила работы': 'working rules',
    'план и память между сессиями': 'plan and memory between sessions',
    'README и код': 'README and code',
    'что уже есть в проекте': 'what the project already has',
    'Части и порядок': 'Parts and order',
    'сначала данные, потом логика, потом экран': 'data first, then logic, then the screen',
    'Договорённости': 'Contracts',
    'интерфейсы, общие типы, схема базы данных': 'interfaces, shared types, database schema',
    'Размер поручения': 'Job size',
    'один небольшой файл или класс': 'one small file or class',
    'Зачем так': 'Why',
    'слабой модели не нужно придумывать — только сделать по описанию': 'a weaker model need not invent — only follow the description',
    'Это нормально': 'That is fine',
    'тесты описывают, что должно получиться': 'tests describe the expected result',
    'Учёт задачи открыт': 'Task tracking started',
    'время и токены не смешаются с прошлой работой': 'time and tokens never mix with earlier work',
    'План записан': 'Plan saved',
    'currentsteps.md — к нему можно вернуться завтра': 'currentsteps.md — pick it up again tomorrow',
    '127.0.0.1 · дашборд': '127.0.0.1 · dashboard',
    'OpenCode · наблюдение за задачей': 'OpenCode · task dashboard',
    'Статус': 'Status',
    'план готов': 'plan ready',
    'Функции': 'Functions',
    'открылся сам — команды вводить не нужно': 'opened by itself — no commands to type',

    # ---- GIF 4: parallel -----------------------------------------------
    'Несколько исполнителей одновременно': 'Several executors at once',
    'Основной проект': 'Main project',
    'две независимые части': 'two independent parts',
    'Две части не зависят друг от друга: бюджет и распорядок дня. Общие договорённости Мастер Чиф зафиксировал заранее.':
        'Two parts do not depend on each other: budget and daily routine. The Master Chief fixed the shared contracts first.',
    'Контроллер делает каждому исполнителю отдельную копию файлов. Основной проект они не трогают.':
        'The controller gives each executor its own copy of the files. They never touch the main project.',
    'Исполнители работают одновременно — каждый в своей копии, со своим учётом и своей сессией.':
        'The executors work at the same time — each in its own copy, with its own tracking and session.',
    'Сторож следит за каждой попыткой: шаги, время и повторы одних и тех же действий. При превышении лимита попытка останавливается.':
        'A watchdog tracks every attempt: steps, time and repeated actions. When a limit is exceeded, the attempt stops.',
    'Мастер Чиф проверяет каждую копию отдельно: что изменилось, тесты именно этой копии, все требования.':
        'The Master Chief reviews each copy separately: what changed, the tests of that very copy, every requirement.',
    'Принятые файлы переносятся в проект по одному. Если файл там успел измениться — перезаписи не будет.':
        'Accepted files are integrated one by one. If the file changed in the project meanwhile, nothing is overwritten.',
    'После переноса — полный набор тестов уже на основном проекте.':
        'After integration — the full test suite runs on the main project.',
    'договорённости': 'contracts',
    'все тесты: 42 из 42 ✓': 'all tests: 42 of 42 ✓',
    '✓ изменения проверены · ✓ тесты копии 5/5 · ✓ ревью': '✓ changes inspected · ✓ copy tests 5/5 · ✓ review',
    'копии, сторож, перенос по одному': 'copies, watchdog, one-by-one integration',
    'budget.py и routine.py не зависят': 'budget.py and routine.py do not depend',
    'друг от друга — можно делать одновременно': 'on each other — they can be built at once',
    'функций готово': 'functions done',
    'копия файлов': 'file copy',
    'перенос': 'integrate',
    '✓ перенесён': '✓ integrated',
    'заготовка': 'skeleton',
    'шаги {a}/24 · время {b} из 10:00 · повторы 0/3': 'steps {a}/24 · time {b} of 10:00 · repeats 0/3',
    'Копия {lab}': 'Copy {lab}',

    # ---- GIF 5: bug fixer ----------------------------------------------
    'Исправитель ошибок: когда и как': 'The Bug Fixer: when and how',
    'Исполнитель': 'Executor',
    'попытка 1': 'attempt 1',
    'попытка 2 — единственная': 'attempt 2 — the only one',
    'Исполнитель сдал работу, но проверка нашла ошибку: пустая категория не отклоняется.':
        'The executor handed in the work, but review found a bug: an empty category is not rejected.',
    'Или сработал лимит: исполнитель исчерпал шаги или время. Контроллер подтверждает, что он остановлен.':
        'Or a limit fired: the executor ran out of steps or time. The controller confirms it has stopped.',
    'Тогда работа один раз переходит исправителю ошибок: тот же файл, те же требования и текст ошибок.':
        'Then the work goes to the Bug Fixer once: the same file, the same requirements and the error output.',
    'Исправитель чинит только тела функций. Мастер Чиф проверяет заново — и принимает.':
        'The Bug Fixer only repairs function bodies. The Master Chief reviews again — and accepts.',
    'Ошибка API, лимит запросов (429), сломанная тестовая среда или пауза — исправителя не зовут.':
        'An API error, a rate limit (429), a broken test setup or a pause never calls the Bug Fixer.',
    'Не справился и исправитель — работа останавливается (STOP) и ждёт решения человека. Обратно исполнителю она не уходит.':
        'If the Bug Fixer fails too, work stops (STOP) and waits for a human decision. It never bounces back to the executor.',
    'тот же файл и те же требования': 'the same file and requirements',
    'публичный текст ошибок тестов': 'the public test error output',
    'свои лимиты шагов и времени': 'its own step and time limits',
    'Исправителя не зовут, если:': 'The Bug Fixer is not called when:',
    'исправитель тоже не справился': 'the Bug Fixer failed too',
    'решает человек: уточнить задание, тесты или модель': 'a human decides: refine the job, the tests or the model',
    '✗ проверка не прошла': '✗ review failed',
    'пустая категория → ошибка?': 'empty category → error?',
    '⏱ лимит попытки': '⏱ attempt limit',
    'шаги 24 из 24 · остановлен ✓': 'steps 24 of 24 · stopped ✓',
    '✓ проверка прошла': '✓ review passed',
    'принято · перенесено в проект': 'accepted · integrated',
    'код + требования + ошибки': 'code + requirements + errors',
    'исправлено': 'fixed',
    'ошибка API или 429': 'API error or 429',
    'это не ошибка кода — ждём или меняем настройку': 'not a code bug — wait or change the setup',
    'сломана тестовая среда': 'broken test setup',
    'чинит Мастер Чиф или спрашивает тебя': 'the Master Chief fixes it or asks you',
    'пауза или отмена': 'pause or cancel',
    'решает пользователь': 'the user decides',

    # ---- GIF 6: final --------------------------------------------------
    'Финал: интерфейс, тесты, отчёт': 'The finish: interface, tests, report',
    'Домашний бюджет': 'Home budget',
    'Покупки за неделю': 'Purchases this week',
    'Ошибка 422': 'Error 422',
    'Цена не может быть отрицательной': 'Price cannot be negative',
    'Все части приняты и перенесены в проект. Остаётся то, что видит пользователь, — интерфейс.':
        'All parts are accepted and integrated. What remains is what the user sees — the interface.',
    'Мастер Чиф запускает приложение и проходит обычные сценарии: добавить запись, изменить, удалить.':
        'The Master Chief runs the app and walks through normal scenarios: add a record, edit it, delete it.',
    'Отмечает, что мешает: бледный текст, кнопка без подписи, непонятное сообщение об ошибке.':
        'It notes what gets in the way: faint text, an unlabeled button, a cryptic error message.',
    'Правки интерфейса — отдельный этап. Логика и договорённости не меняются, тесты снова проходят.':
        'Interface fixes are a separate phase. Logic and contracts stay the same, tests pass again.',
    'Финал: полный набор тестов, отчёт и файл запуска. Если интерфейс проверить не удалось, это отмечается в отчёте.':
        'Finish: the full test suite, a report and a launch file. If the interface could not be checked, the report notes it.',
    'Молоко': 'Milk',
    '2 шт': '2 pcs',
    'Хлеб': 'Bread',
    '1 шт': '1 pc',
    'Яблоки': 'Apples',
    '1,5 кг': '1.5 kg',
    '178 ₽': '$2.40',
    '62 ₽': '$1.10',
    '210 ₽': '$3.20',
    '+ Добавить покупку': '+ Add purchase',
    'код готов — но удобно ли им пользоваться?': 'the code is done — but is it pleasant to use?',
    'добавить покупку': 'add a purchase',
    'изменить запись': 'edit a record',
    'ввести неверную цену': 'enter a wrong price',
    'Только интерфейс': 'Interface only',
    'подписи, контраст, понятные сообщения': 'labels, contrast, clear messages',
    'Тесты снова зелёные': 'Tests green again',
    'логика и договорённости те же': 'same logic and contracts',
    '✓ принят · ✓ перенесён': '✓ accepted · ✓ integrated',
    'бледный текст — плохо читается': 'faint text — hard to read',
    'кнопка «+» без подписи': 'a "+" button without a label',
    'сообщение «Ошибка 422» непонятно': '"Error 422" means nothing to a user',
    'Полный набор тестов': 'Full test suite',
    '42 из 42 ✓ на основном проекте': '42 of 42 ✓ on the main project',
    'Отчёт': 'Report',
    'время, токены по ролям и попыткам, возвраты': 'time, tokens per role and attempt, reworks',
    'Файл запуска': 'Launch file',
    'run.ps1 — как запустить приложение': 'run.ps1 — how to start the app',

    # ---- GIF 7: models -------------------------------------------------
    'Модели, лимиты и ключи': 'Models, limits and keys',
    'Адрес API': 'API address',
    '✓ Ключ найден': '✓ Key found',
    'OPENROUTER_API_KEY — вводить снова не нужно': 'OPENROUTER_API_KEY — no need to enter it again',
    'Связь установлена. OpenRouter принял ключ.': 'Connected. OpenRouter accepted the key.',
    'Настройки сохранены.': 'Settings saved.',
    'Настройки подготовлены.': 'Settings prepared.',
    'Окно «Модели проекта»: у каждой роли своя модель. Открывается из мастера установки или кнопкой «Настройки моделей» в дашборде.':
        '"Project models": every role has its own model. It opens from the setup wizard or the "Model settings" button in the dashboard.',
    'Источник модели: модель из OpenCode или свой API. Исполнителям доступна ещё и LM Studio на своём компьютере.':
        'Model source: a model from OpenCode or your own API. Executors can also use LM Studio on your computer.',
    'Исполнители: сколько работает одновременно и лимиты одной попытки. 1 — по очереди, 2 и больше — параллельно.':
        'Executors: how many run at once and the limits of one attempt. 1 = one after another, 2+ = in parallel.',
    'Исправитель ошибок: своя модель и свои лимиты. Его можно выключить.':
        'Bug Fixer: its own model and its own limits. It can be switched off.',
    'Каталог OpenRouter: отфильтруй модели для кода, щёлкни строку — модель подставится в выбранную роль.':
        'OpenRouter catalog: filter coding models, click a row — the model fills in the chosen role.',
    'Ключ хранится в Windows. «Проверить связь» → «Сохранить настройки» → «Подготовить OpenCode» → новый чат build.':
        'The key lives in Windows. "Check connection" → "Save settings" → "Prepare OpenCode" → a new build chat.',
    'Локально · LM Studio': 'Local · LM Studio',
    'Модель из OpenCode': 'Model from OpenCode',
    'Свой API': 'Own API',
    'Загруженная модель': 'Loaded model',
    'Модель OpenCode': 'OpenCode model',
    'Модель': 'Model',
    'Шагов на попытку': 'Steps per attempt',
    'Секунд на попытку': 'Seconds per attempt',
    'или источник «Выключен» — исправителя не будет': 'or source "Disabled" — no Bug Fixer at all',
    '✓ Для кода': '✓ For coding',
    '✓ Только с инструментами': '✓ Tool support only',
    'Бесплатные': 'Free models',
    'Подставить в:': 'Assign to:',
    'условные данные · цены — $ за 1 млн токенов': 'sample data · prices in $ per 1M tokens',
    'Проверить связь': 'Check connection',
    'архитектура, проверка, интерфейс': 'architecture, review, interface',
    'пишут код поручений': 'write the code of each job',
    'одна попытка исправления': 'one correction attempt',
    'Одновременных исполнителей': 'Concurrent executors',
    'Повторов без прогресса': 'Repeated actions without progress',
    'Текущий чат не переключится': 'The current chat will not switch',
    'открой новый чат build': 'open a new build chat',
    'Добавил новый ключ?': 'Added a new key?',
    'полностью перезапусти Desktop': 'fully restart Desktop',
    'Для каждой папки': 'Per folder',
    'выбор хранится в .opencode/kit-models.json': 'saved in .opencode/kit-models.json',
    'Без ключей в файлах': 'No keys in files',
    'в файле только имя переменной Windows': 'the file stores only a Windows variable name',
    'модели, которые OpenCode уже знает, в т. ч. бесплатные': 'models OpenCode already knows, free ones included',
    'только для исполнителей: локально, модель загружаешь ты': 'executors only: local, you load the model',
    'адрес …/v1, ключ и точное имя модели': '…/v1 address, key and exact model ID',
    '1 — по очереди': '1 — one after another',
    'надёжный режим по умолчанию': 'the safe default',
    '2 и больше — параллельно': '2+ — in parallel',
    'только для частей, которые не зависят друг от друга': 'only for parts that do not depend on each other',
    'Лимиты попытки': 'Attempt limits',
    'перебор шагов, времени или повторов — остановка': 'too many steps, too long or repeating — stop',
    'Когда работает': 'When it runs',
    'после ошибки кода или лимита исполнителя — одна попытка': 'after a code bug or an executor limit — one attempt',
    'Когда нет': 'When not',
    'ошибки API и 429 его не запускают': 'API errors and 429 never start it',
    'Каталог без ключа': 'Catalog without a key',
    'грузится сам; цены — вход / выход': 'loads by itself; prices — input / output',
    'Щелчок ничего не сохраняет': 'A click saves nothing',
    'роль получает адрес OpenRouter и ID модели': 'the role gets the OpenRouter address and model ID',

    # ---- GIF 8: dashboard ----------------------------------------------
    'Язык: Русский': 'Language: English',
    'Дашборд: видно каждого исполнителя': 'The dashboard: every executor in view',
    'Настройки моделей': 'Model settings',
    'выполняется': 'running',
    'Дашборд открывается сам, когда Мастер Чиф начинает задачу. Язык — как в браузере; переключатель «Язык» запоминает выбор.':
        'The dashboard opens when the Master Chief starts the task. Language follows the browser; the "Language" switch remembers your choice.',
    '«Сейчас в работе»: видно каждого участника — какой исполнитель над какой функцией работает.':
        '"Working now": every participant is visible — which executor works on which function.',
    '«Детализация работ»: все попытки по каждому заданию — кто делал, чем закончилось, перенесено ли в проект.':
        '"Work details": every attempt of each job — who did it, how it ended, whether it was integrated.',
    '«Токены»: расход по моделям и отдельно по каждой попытке. Если части данных нет, сумма помечается «≥».':
        '"Tokens": usage per model and per attempt. If some data is missing, the sum is marked "≥".',
    '«Приостановить» останавливает Мастер Чифа и всех исполнителей сразу. «Продолжить» — та же задача, с того же плана.':
        '"Pause" stops the Master Chief and all executors at once. "Resume" continues the same task from the same plan.',
    'В конце — итог: ссылка на папку проекта, файл запуска и итоговый отчёт.':
        'At the end — the summary: project folder, launch file and the final report.',
    '⏸ Приостановить': '⏸ Pause',
    '▶ Продолжить': '▶ Resume',
    '■ Остановить': '■ Cancel',
    'Удалить задачу…': 'Delete task…',
    'Обзор': 'Overview',
    'Детализация работ': 'Work details',
    'Токены': 'Tokens',
    'Сейчас в работе': 'Working now',
    'Исполнитель A': 'Executor A',
    'Исполнитель B': 'Executor B',
    '✓ Работа завершена': '✓ Work completed',
    'Полный набор: 42 теста, OK · 4 задания приняты · 1 исправление': 'Full suite: 42 tests, OK · 4 jobs accepted · 1 fix',
    'пауза': 'paused',
    'приостанавливается…': 'Pausing…',
    'Удалить': 'Delete',
    ' · пауза': ' · paused',
    'работает': 'working',
    'Открыть папку проекта': 'Open project folder',
    'Посмотреть файл запуска': 'View launch file',
    'Итоговый отчёт': 'Final report',
    'Возвраты на доработку': 'Rework requests',
    'Успешные прогоны / все': 'Successful runs / all',
    'Сбои исполнителя': 'Executor failures',
    'Модель / роль': 'Model / role',
    'Вход': 'Input',
    'Выход': 'Output',
    '≥ — у части сообщений нет данных; ноль не подставляется. Рядом — расход по каждой попытке.':
        '≥ means some messages have no data; zero is never substituted. Usage per attempt is shown alongside.',
    'Основная модель и все связанные исполнители приостановлены.': 'The main model and all linked executors are paused.',
    'Попытка 1 · Исполнитель A': 'Attempt 1 · Executor A',
    'возврат: пустая категория': 'rework: empty category',
    'Попытка 2 · Bug Fixer': 'Attempt 2 · Bug Fixer',
    'принято · изменения объединены': 'accepted · changes integrated',
    'Попытка 1 · Исполнитель B': 'Attempt 1 · Executor B',
    'Исполнители · MiMo': 'Executors · MiMo',

    # ---- live installer GIF (build_installer_gif.py) ----------------------
    'Мастер установки': 'Setup wizard',
    'Двойной щелчок по install.cmd открывает мастер. Он уже нашёл OpenCode Desktop.':
        'Double-clicking install.cmd opens the wizard. It has already found OpenCode Desktop.',
    'Шаг 2: путь к папке проекта. Недостающие папки мастер создаст сам.':
        'Step 2: the project folder path. Missing folders are created for you.',
    'Шаг 3: «Создать проект и настроить модели» — кит копируется в папку проекта.':
        'Step 3: "Create project and configure models" — the kit is copied into the project folder.',
    'Открылось окно моделей. Мастер Чиф берёт модель из настроек проекта.':
        'The model window opens. The Master Chief uses the model from the project defaults.',
    'Исполнители: бесплатная MiMo V2.6 Flash, сколько работает одновременно и лимиты одной попытки.':
        'Executors: free MiMo V2.6 Flash, how many run at once and the limits of one attempt.',
    'Исправитель ошибок: бесплатная DeepSeek V4.1 Flash и свои лимиты шагов и времени.':
        'Bug Fixer: free DeepSeek V4.1 Flash with its own step and time limits.',
    '«Подготовить OpenCode» сохраняет выбор и собирает настройки. Модель при этом не вызывается.':
        '"Prepare OpenCode" saves the choice and builds the settings. No model is called.',
    'Готово: кнопка «Открыть проект в OpenCode». Мастер запускает Desktop с этой папкой.':
        'Done: "Open project in OpenCode". The wizard launches Desktop with this folder.',
    'Шаг 4: «Копировать задание» — вставь его в новый чат build и отправь сам.':
        'Step 4: "Copy prompt" — paste it into a new build chat and send it yourself.',
}
