"""GIF 4: working with LM Studio and OpenRouter."""
from gifkit import *

STEPS = [
    dict(cap='LM Studio: ты сам загружаешь модель (контекст, GPU и прочие параметры) и включаешь '
             'сервер. Кит использует эту загрузку и никогда не вызывает Load/Unload.', T=16, hold=4400),
    dict(cap='run_opencode.py читает /api/v1/models: поле loaded_instances показывает реально '
             'загруженные экземпляры. Embedding-модели пропускаются.', T=24, hold=4200),
    dict(cap='Одна загруженная LLM — используется она. Несколько — та, что выбрана в настройках, '
             'иначе кит покажет ID и попросит выбрать. Ни одной — попросит загрузить.', T=22, hold=4800),
    dict(cap='Выбор пишется в надстройку .opencode/opencode.jsonc: executor и executor-fast '
             'получают один загруженный экземпляр. Мастер Чиф и права не меняются.', T=22, hold=4400),
    dict(cap='check_env.py проверяет конфиг, связь с LM Studio и короткий пробный ответ. '
             'Сменил модель в LM Studio — запусти подготовку заново.', T=20, hold=4000),
    dict(cap='OpenRouter: в конфигураторе раздел «OpenRouter — Каталог и цены». Публичный каталог '
             'грузится без ключа; цены — USD за 1 млн токенов, вход и выход отдельно.', T=20, hold=4400),
    dict(cap='Фильтры: «Для кода», «Только с инструментами» (агентам они нужны) и «Бесплатные». '
             'Таблица ниже — условные данные для примера.', T=24, hold=4400),
    dict(cap='Выбери роль в «Подставить в:» и щёлкни строку: роль получает «Свой API», адрес '
             'https://openrouter.ai/api/v1 и точный ID модели с окончанием :free.', T=26, hold=4600),
    dict(cap='«К настройкам роли»: сохранённый ключ OPENROUTER_API_KEY виден как «Ключ найден». '
             '«Проверить связь» → OpenRouter принял ключ. Затем сохранить и подготовить.', T=30, hold=4800),
    dict(cap='Другой путь: подключить OpenRouter в OpenCode через /connect и выбрать '
             '«Модель из OpenCode», например openrouter/…:free. LM Studio тогда не опрашивается.',
         T=18, hold=4400),
    dict(cap='В отчёте токены делятся на группы: lmstudio — локальные, OpenRouter «:free» — '
             'бесплатные облачные, остальные — платные. Нет данных — «неизвестно», а не ноль.',
         T=22, hold=5200),
]

CHIPS = [('LM Studio', (0, 4), GREEN), ('OpenRouter', (5, 9), PURPLE), ('Учёт токенов', (10, 10), CYAN)]


def chips(c, s):
    x = 30
    for label, (a, b), col in CHIPS:
        act = a <= s <= b
        done = s > b
        w = c.tlen(label, 15, 's') + 30
        cc = col if (act or done) else BORDER
        c.rr(x, 74, w, 32, mix(cc, 0.22) if act else PANEL, cc, 2, 16)
        c.t(x + w / 2, 90, label, 15, 's', TEXT if (act or done) else MUTED, anchor='mm',
            bg=mix(cc, 0.22) if act else PANEL)
        x += w + 12


def lmstudio_window(c, x, y, w, h, a=1.0, active=False, skip_embed=False):
    top = c.window(x, y, w, h, 'LM Studio · Developer', a, active, GREEN)
    c.d.ellipse([x + 18, top + 4, x + 30, top + 16], fill=mix(GREEN, a, PANEL))
    c.t(x + 40, top + 10, 'Server: Running · localhost:1234', 14, 's', GREEN, a, anchor='lm', bg=PANEL)
    c.t(x + 18, top + 34, 'Загруженные модели', 13, 's', MUTED, a, bg=PANEL)
    rows = [('coder-32b-instruct', 'LLM · ctx 32768 · GPU max', TEXT, False),
            ('text-embedding-model', 'Embedding', MUTED, True)]
    for i, (name, info, col, emb) in enumerate(rows):
        ry = top + 58 + i * 52
        c.rr(x + 16, ry, w - 32, 44, PANEL2, None, 0, 8, a, bg=PANEL)
        c.t(x + 30, ry + 6, name, 14, 'm', col, a, bg=PANEL2)
        c.t(x + 30, ry + 25, info, 12, 'r', MUTED, a, bg=PANEL2)
        if emb and skip_embed:
            c.d.line([(x + 28, ry + 14), (x + 30 + c.tlen(name, 14, 'm'), ry + 14)],
                     fill=mix(RED, a, PANEL2), width=2)
            c.tag(x + w - 26, ry + 11, 'пропущена', RED, a, right=True, size=12)
        elif not emb and skip_embed:
            c.tag(x + w - 26, ry + 11, 'выбрана', GREEN, a, right=True, size=12)


def scene_lm(c, s, p):
    lmstudio_window(c, 40, 124, 560, 230, 1, True)
    notes = [('Модель и её параметры выбираешь ты', 'размер контекста, распределение по GPU и др.'),
             ('Кит не вызывает Load / Unload', 'и не отправляет параметры загрузки'),
             ('Не выгружай модель во время задачи', 'выбор делается до запуска, а не перед каждым токеном')]
    for i, (t1, t2) in enumerate(notes):
        a = seg(p, 0.2 + i * 0.2, 0.4 + i * 0.2)
        c.node(640, 124 + i * 100, 520, 80, t1, t2, GREEN, a, tsize=17, ssize=13)


def scene_api(c, s, p):
    c.node(40, 140, 300, 96, 'run_opencode.py', 'или --prepare-only в Desktop', BLUE, 1, True)
    lmstudio_window(c, 600, 124, 560, 230, 1, False, skip_embed=p > 0.75)
    c.arrow([(340, 175), (598, 175)], BLUE, 1, 3, seg(p, 0.05, 0.3))
    c.t(360, 150, 'GET /api/v1/models', 14, 'm', BLUE, seg(p, 0.05, 0.2))
    c.packet([(598, 300), (340, 300)], seg(p, 0.35, 0.65), 'loaded_instances', GREEN, 1 - seg(p, 0.68, 0.74))
    c.arrow([(598, 300), (340, 300), (190, 300), (190, 238)], GREEN, seg(p, 0.6, 0.7), 2, seg(p, 0.6, 0.75))
    c.rr(40, 380, 1120, 168, PANEL, BORDER, 1, 12)
    c.para(60, 396, 'Общий список /v1/models показывает и незагруженные модели. Поле loaded_instances '
                    'нового API отличает реально загруженные экземпляры — именно их кит и использует.',
           1080, 16, 'r', TEXT, seg(p, 0.3, 0.5), bg=PANEL)
    c.para(60, 466, 'Embedding-модели нужны для поиска и векторов, а не для написания кода, '
                    'поэтому в выбор исполнителя не попадают.', 1080, 16, 'r', MUTED, seg(p, 0.75, 0.9),
           bg=PANEL)


def scene_choose(c, s, p):
    c.rr(440, 124, 320, 70, PANEL2, BLUE, 2, 35)
    c.t(600, 159, 'Сколько загружено LLM?', 17, 's', TEXT, anchor='mm', bg=PANEL2)
    branches = [
        ('одна', 'используется она — даже если в конфиге указана другая', GREEN, 40),
        ('несколько', 'выбранная в настройках (executor / instance); если неоднозначно — '
                      'кит показывает ID: run_opencode.py --model "ID"', YELLOW, 420),
        ('ни одной', 'кит просит загрузить модель в LM Studio и ничего не запускает', RED, 800),
    ]
    for i, (lab, text, col, x) in enumerate(branches):
        a = seg(p, 0.15 + i * 0.22, 0.35 + i * 0.22)
        c.arrow([(600, 194), (600, 222), (x + 180, 222), (x + 180, 262)], col, a, 2, a)
        c.tag(x + 180 - c.tlen(lab, 14, 's') / 2 - 9, 232, lab, col, a, size=14)
        c.rr(x, 266, 360, 150, PANEL, col, 2, 12, a)
        c.para(x + 18, 282, text, 324, 16, 'r', TEXT, a, bg=PANEL)
    c.para(40, 440, 'Указать незагруженную модель через --model — ошибка: кит не подменяет её другой '
                    'и не запускает OpenCode.', 1120, 16, 'r', MUTED, seg(p, 0.85, 1))


def scene_overlay(c, s, p):
    top = c.window(40, 124, 620, 250, '.opencode/opencode.jsonc  (надстройка, упрощённо)', 1, True, PURPLE)
    js = [('// generated by kit/run_opencode.py', MUTED),
          ('"providers": { "lmstudio": { "models": {', TEXT),
          ('  "loaded-executor": { "modelID": "coder-32b-instruct" }', GREEN),
          ('}}},', TEXT),
          ('"agents": {', TEXT),
          ('  "executor":      { "model": "lmstudio/loaded-executor" },', TEXT),
          ('  "executor-fast": { "model": "lmstudio/loaded-executor" }', TEXT),
          ('}', TEXT)]
    tot = sum(len(t) + 1 for t, _ in js)
    c.code(60, top + 4, js, tot * seg(p, 0.05, 0.6), 1, 14, 24)
    c.t(680, 130, 'Как запускается', 17, 's', TEXT)
    modes = [('OpenCode Desktop уже открыт', 'py kit/run_opencode.py --prepare-only --reload', BLUE),
             ('Из терминала', 'py kit/run_opencode.py  (свой сервер, переменные OPENCODE_KIT_*)', GREEN)]
    for i, (t1, t2, col) in enumerate(modes):
        a = seg(p, 0.55 + i * 0.18, 0.7 + i * 0.18)
        c.node(680, 166 + i * 108, 480, 92, t1, t2, col, a, tsize=16, ssize=13)
    c.para(40, 400, '«fast» — это роль, а не другая маленькая модель: оба исполнителя работают на одном '
                    'загруженном экземпляре. Исходный opencode.jsonc с комментариями не переписывается.',
           1120, 16, 'r', MUTED, seg(p, 0.6, 0.8))


def scene_check(c, s, p):
    top = c.window(40, 124, 760, 260, 'PowerShell', 1, True, GREEN)
    lines = [('> py kit/check_env.py', TEXT), ('opencode.jsonc ........ OK', GREEN),
             ('LM Studio server ...... OK  (localhost:1234)', GREEN),
             ('loaded instance ....... coder-32b-instruct', GREEN),
             ('probe reply ........... OK', GREEN)]
    for i, (t, col) in enumerate(lines):
        c.t(60, top + 6 + i * 32, t, 16, 'm', col, seg(p, 0.1 + i * 0.15, 0.2 + i * 0.15))
    c.node(830, 140, 330, 110, 'pipeline_smoke.py', 'офлайн-проверка цепочки Мастер Чиф → исполнитель',
           BLUE, seg(p, 0.75, 0.9), tsize=17)


ROWS = [
    ('vendor-a/coder-pro', '256K', True, '1.20', '4.80', True, False),
    ('vendor-b/dev-mini:free', '128K', True, '0', '0', True, True),
    ('vendor-c/chat-large', '200K', False, '3.00', '15.00', False, False),
    ('vendor-d/code-flash', '1M', True, '0.30', '1.20', True, False),
    ('vendor-e/agent-coder:free', '64K', True, '0', '0', True, True),
]


def catalog(c, x, y, w, h, s, p, filt=0.0, pick=0.0, assign_hl=False):
    top = c.window(x, y, w, h, 'Модели проекта — OpenCode Kit', 1)
    bw = 222
    tabs = [('Мастер Чиф', 'Архитектура и ревью'), ('Исполнители', 'Реализация кода'),
            ('OpenRouter', 'Каталог и цены')]
    for i, (t1, t2) in enumerate(tabs):
        bx = x + 16 + i * (bw + 10)
        act = i == 2
        c.rr(bx, top, bw, 50, mix(BLUE, 0.22, PANEL) if act else PANEL2, BLUE if act else BORDER, 2, 8, bg=PANEL)
        c.t(bx + 14, top + 6, t1, 15, 's', TEXT, bg=PANEL2)
        c.t(bx + 14, top + 28, t2, 13, 'r', MUTED, bg=PANEL2)
    fy = top + 64
    fl = [('Для кода', filt > 0.2), ('Только с инструментами', True), ('Бесплатные', filt > 0.6)]
    fx = x + 16
    for lab, on in fl:
        fw = c.tlen(lab, 13, 's') + 34
        c.rr(fx, fy, fw, 28, mix(PURPLE, 0.3, PANEL) if on else PANEL2, PURPLE if on else BORDER, 2, 14, bg=PANEL)
        c.t(fx + 12, fy + 14, ('✓ ' if on else '') + tr(lab), 13, 's', TEXT if on else MUTED, anchor='lm',
            bg=mix(PURPLE, 0.3, PANEL) if on else PANEL2)
        fx += fw + 8
    c.t(x + w - 16, fy + 14, 'Подставить в:', 13, 'r', MUTED, anchor='rm', bg=PANEL)
    c.rr(x + w - 220, fy + 34, 204, 28, mix(ORANGE, 0.3, PANEL) if assign_hl else PANEL2,
         ORANGE if assign_hl else BORDER, 2, 6, bg=PANEL)
    c.t(x + w - 208, fy + 48, tr('Исполнители  ▾').replace('▾', 'v'), 13, 's', TEXT, anchor='lm', bg=PANEL2)
    hy = fy + 72
    cols = [(x + 20, 'Модель · API ID'), (x + 330, 'Контекст'), (x + 420, 'Инструменты'),
            (x + 530, 'Вход $/1M'), (x + 620, 'Выход $/1M')]
    for cx, lab in cols:
        c.t(cx, hy, lab, 12, 's', MUTED, bg=PANEL)
    c.d.line([(x + 16, hy + 22), (x + w - 16, hy + 22)], fill=BORDER)
    ry = hy + 30
    for name, ctx, tools, pin, pout, code, free in ROWS:
        visible = 1.0
        if not code:
            visible *= 1 - seg(filt, 0.1, 0.3)
        if not free:
            visible *= 1 - seg(filt, 0.5, 0.7)
        if visible <= 0.02:
            continue
        rh = 34 * visible
        sel = pick > 0 and name == 'vendor-e/agent-coder:free'
        if sel:
            c.rr(x + 14, ry - 3, w - 28, 30, mix(BLUE, 0.35 * pick, PANEL), BLUE, 1, 6, bg=PANEL)
        a = visible
        rowbg = mix(BLUE, 0.35 * pick, PANEL) if sel else PANEL
        c.t(x + 20, ry + 4, name, 13, 'm', TEXT, a, bg=rowbg)
        c.t(x + 330, ry + 4, ctx, 13, 'm', TEXT, a, bg=rowbg)
        c.t(x + 420, ry + 4, 'Да' if tools else 'Нет', 13, 'r', GREEN if tools else MUTED, a, bg=rowbg)
        c.t(x + 530, ry + 4, pin, 13, 'm', GREEN if free else TEXT, a, bg=rowbg)
        c.t(x + 620, ry + 4, pout, 13, 'm', GREEN if free else TEXT, a, bg=rowbg)
        ry += rh
    c.t(x + 16, y + h - 26, 'условные данные · реальный каталог: openrouter.ai/api/v1/models', 12, 'r', DIM, bg=PANEL)
    return ry


def scene_catalog(c, s, p):
    catalog(c, 40, 120, 740, 458, s, p)
    notes = [('Каталог без ключа', 'грузится при открытии раздела; кэш — .metrics/.openrouter-catalog.json'),
             ('Цены каталога', 'USD за 1 млн токенов: вход и выход отдельно; «—» — цена неизвестна'),
             ('«Обновить цены»', 'без интернета показан прежний каталог с пометкой давности')]
    for i, (t1, t2) in enumerate(notes):
        a = seg(p, 0.2 + i * 0.2, 0.4 + i * 0.2)
        c.node(800, 120 + i * 118, 360, 100, t1, t2, PURPLE, a, tsize=16, ssize=13)


def scene_filter(c, s, p):
    catalog(c, 40, 120, 740, 458, s, p, filt=seg(p, 0.1, 0.9))
    c.node(800, 120, 360, 130, '«Для кода»', 'подборка programming + упоминание кода в описании. '
                                            'Это способ отбора, а не рейтинг качества.', PURPLE,
           seg(p, 0.1, 0.3), tsize=16, ssize=13)
    c.node(800, 266, 360, 100, 'Инструменты', 'включено по умолчанию: без tool calling агент не работает',
           PURPLE, seg(p, 0.35, 0.5), tsize=16, ssize=13)
    c.node(800, 382, 360, 100, 'Бесплатные', 'определяются по опубликованным ставкам; ID оканчивается на :free',
           GREEN, seg(p, 0.6, 0.8), tsize=16, ssize=13)


def scene_pick(c, s, p):
    catalog(c, 40, 120, 740, 458, s, p, filt=1.0, pick=seg(p, 0.45, 0.55), assign_hl=0.1 < p < 0.4)
    cx = 700 - 300 * seg(p, 0.3, 0.42)
    cy = 268 + 70 * seg(p, 0.3, 0.42)
    c.cursor((cx, cy), seg(p, 0.0, 0.08) * (1 - seg(p, 0.85, 0.9)),
             click=seg(p, 0.12, 0.25) if p < 0.3 else seg(p, 0.44, 0.56))
    a = seg(p, 0.55, 0.7)
    top = c.window(800, 120, 360, 300, 'черновик роли · Исполнители', a, True, ORANGE)
    lines = [('Источник', 'Свой API'), ('Адрес API', 'https://openrouter.ai/api/v1'),
             ('Модель', 'vendor-e/agent-coder:free')]
    for i, (k, v) in enumerate(lines):
        c.t(818, top + 6 + i * 62, k, 13, 's', MUTED, a, bg=PANEL)
        c.t(818, top + 28 + i * 62, v, 14 if i else 15, 'm', TEXT, a, bg=PANEL)
    c.para(818, top + 196, 'Щелчок ничего не сохраняет и не запускает генерацию.', 324, 13, 'r', YELLOW, a,
           bg=PANEL)
    c.t(800, 440, 'Мастер Чиф выбирается так же —', 15, 'r', MUTED, seg(p, 0.8, 1))
    c.t(800, 462, 'другой ролью в «Подставить в:».', 15, 'r', MUTED, seg(p, 0.8, 1))


def scene_key(c, s, p):
    top = c.window(40, 120, 720, 458, 'Модели проекта — OpenCode Kit · Исполнители', 1)
    c.t(60, top + 10, '1. Адрес API', 13, 's', MUTED, bg=PANEL)
    c.rr(60, top + 30, 470, 34, PANEL2, BORDER, 2, 6, bg=PANEL)
    c.t(72, top + 47, 'https://openrouter.ai/api/v1', 14, 'm', TEXT, anchor='lm', bg=PANEL2)
    c.button(546, top + 30, 150, 34, 'Проверить связь', GREEN, 1, size=13, active=0.3 < p < 0.5)
    c.t(60, top + 80, '✓ Ключ найден', 14, 's', GREEN, bg=PANEL)
    c.t(74 + c.tlen('✓ Ключ найден', 14, 's'), top + 81, 'OPENROUTER_API_KEY · повторно вводить не нужно', 13, 'm', MUTED, bg=PANEL)
    c.t(60, top + 106, '2. Заменить API-ключ (необязательно)', 13, 's', MUTED, bg=PANEL)
    c.rr(60, top + 126, 636, 34, PANEL2, BORDER, 2, 6, bg=PANEL)
    c.t(72, top + 143, 'будет использован сохранённый ключ', 14, 'r', DIM, anchor='lm', bg=PANEL2)
    c.t(60, top + 176, '3. Модель', 13, 's', MUTED, bg=PANEL)
    c.rr(60, top + 196, 470, 34, PANEL2, BORDER, 2, 6, bg=PANEL)
    c.t(72, top + 213, 'vendor-e/agent-coder:free', 14, 'm', TEXT, anchor='lm', bg=PANEL2)
    a = seg(p, 0.45, 0.55)
    c.t(60, top + 250, 'Связь установлена. OpenRouter принял ключ.', 14, 's', GREEN, a, bg=PANEL)
    c.t(60, top + 272, 'Генерация модели и инструменты не проверялись.', 14, 'r', MUTED, a, bg=PANEL)
    by = 120 + 458 - 52
    c.button(56, by, 190, 34, 'Сохранить настройки', BLUE, 1, True, active=0.6 < p < 0.75, size=14)
    c.button(258, by, 200, 34, 'Подготовить OpenCode', BLUE, 1, active=p > 0.78, size=14)
    if p < 0.55:
        cx, cy = 620, top + 47
    elif p < 0.76:
        cx, cy = 620 - 470 * seg(p, 0.55, 0.6), top + 47 + (by + 18 - top - 47) * seg(p, 0.55, 0.6)
    else:
        cx, cy = 150 + 208 * seg(p, 0.76, 0.8), by + 18
    click = seg(p, 0.33, 0.45) if p < 0.55 else (seg(p, 0.62, 0.72) if p < 0.76 else seg(p, 0.82, 0.92))
    c.cursor((cx, cy), seg(p, 0.2, 0.3), click=click)
    c.node(800, 120, 360, 130, 'Ключ — в Windows', 'переменная пользователя; в kit-models.json только её имя',
           YELLOW, seg(p, 0.05, 0.2), tsize=16, ssize=13)
    c.node(800, 266, 360, 130, 'Один ключ на две роли', 'OPENROUTER_API_KEY подходит и Мастер Чифу, и исполнителям',
           GREEN, seg(p, 0.2, 0.35), tsize=16, ssize=13)
    c.node(800, 412, 360, 130, 'Новый ключ?', 'полностью перезапусти Desktop, чтобы он увидел новое окружение',
           ORANGE, seg(p, 0.85, 1), tsize=16, ssize=13)


def scene_connect(c, s, p):
    top = c.window(40, 124, 520, 200, 'OpenCode', 1, True, BLUE)
    c.t(60, top + 6, '> /connect', 18, 'm', TEXT, seg(p, 0.05, 0.2))
    c.t(60, top + 40, 'provider: OpenRouter ......... OK', 16, 'm', GREEN, seg(p, 0.2, 0.35))
    c.t(60, top + 74, 'модели OpenRouter доступны OpenCode', 15, 'r', MUTED, seg(p, 0.3, 0.45))
    top2 = c.window(600, 124, 560, 200, '.opencode/kit-models.json', seg(p, 0.45, 0.6), False, GREEN)
    js = [('"executors": {', TEXT), ('  "source": "opencode",', TEXT),
          ('  "model": "openrouter/vendor-e/agent-coder:free"', YELLOW), ('}', TEXT)]
    c.code(620, top2 + 6, js, None, seg(p, 0.45, 0.6), 14, 26)
    c.rr(40, 350, 1120, 190, PANEL, BORDER, 1, 12)
    rows = [('LM Studio', 'source: lmstudio', 'локально, без оплаты API; модель загружена у тебя', GREEN),
            ('OpenRouter через /connect', 'source: opencode', 'ключ хранит OpenCode', BLUE),
            ('OpenRouter как свой API', 'source: api', 'ключ — переменная Windows (OPENROUTER_API_KEY)', PURPLE)]
    for i, (t1, t2, t3, col) in enumerate(rows):
        a = seg(p, 0.6 + i * 0.12, 0.7 + i * 0.12)
        y = 368 + i * 54
        c.d.ellipse([60, y + 6, 72, y + 18], fill=mix(col, a, PANEL))
        c.t(86, y, t1, 16, 's', TEXT, a, bg=PANEL)
        c.t(390, y + 2, t2, 14, 'm', col, a, bg=PANEL)
        c.t(590, y, t3, 15, 'r', MUTED, a, bg=PANEL)


def scene_tokens(c, s, p):
    groups = [('Локальные / бесплатные', 'все модели провайдера lmstudio', 'исполнитель на LM Studio', GREEN),
              ('Бесплатные облачные', 'модели OpenRouter с окончанием :free', 'исполнитель …:free', CYAN),
              ('Платные', 'все остальные известные провайдеры', 'обычно Мастер Чиф', ORANGE)]
    for i, (t1, t2, t3, col) in enumerate(groups):
        x = 40 + i * 380
        a = seg(p, 0.1 + i * 0.2, 0.3 + i * 0.2)
        c.rr(x, 130, 360, 260, PANEL, col, 3, 14, a)
        c.t(x + 20, 150, t1, 19, 'b', col, a, bg=PANEL)
        c.para(x + 20, 186, t2, 320, 15, 'r', TEXT, a, bg=PANEL)
        c.t(x + 20, 250, 'пример:', 13, 's', MUTED, a, bg=PANEL)
        c.t(x + 20, 270, t3, 15, 'r', TEXT, a, bg=PANEL)
        c.t(x + 20, 320, 'вход · выход · рассуждения · кэш', 13, 'r', MUTED, a, bg=PANEL)
        c.t(x + 20, 342, 'считаются отдельно', 13, 'r', MUTED, a, bg=PANEL)
    c.para(40, 420, 'Счётчики берутся из экспорта сессий OpenCode (основной и дочерних) за время задачи. '
                    'Денежную стоимость скрипт не считает; недостающие данные остаются «неизвестно».',
           1120, 16, 'r', MUTED, seg(p, 0.75, 0.95))


SCENES = [scene_lm, scene_api, scene_choose, scene_overlay, scene_check, scene_catalog, scene_filter,
          scene_pick, scene_key, scene_connect, scene_tokens]


def draw(c, s, p):
    chips(c, s)
    SCENES[s](c, s, p)


if __name__ == '__main__':
    n = build('../04_lmstudio_openrouter.gif', STEPS, draw, 'GIF 4/5', 'Модели: LM Studio и OpenRouter')
    print('frames', n)
