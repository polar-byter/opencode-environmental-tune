"""GIF 3: preparing a project for a new task: kit, AGENTS.md, models, task intake."""
from gifkit import *

STEPS = [
    dict(cap='Новый проект: скопируй в него opencode.jsonc, AGENTS.md, .opencode/commands/ и kit/. '
             'Кит не зависит от языка проекта.', T=26, hold=3800),
    dict(cap='В AGENTS.md меняются только разделы «# EDIT»: команда тестов, папки, имя плана. '
             'Одна проверка check подтверждает, что результат тестов читается.', T=34, hold=4400),
    dict(cap='У каждой роли свой источник модели: LM Studio, модель, уже подключённая в OpenCode, '
             'или любой OpenAI-совместимый API.', T=18, hold=4400),
    dict(cap='Конфигуратор (кнопка «Настройки моделей» в дашборде). Мастер Чиф → «Модель из OpenCode»: '
             'подключения, уже известные OpenCode через /connect.', T=22, hold=4200),
    dict(cap='Исполнители → «Свой API»: адрес …/v1, ключ, модель. «Проверить связь» и «Получить '
             'модели» ничего не генерируют и не сохраняют.', T=48, hold=4600),
    dict(cap='«Сохранить настройки» → .opencode/kit-models.json для этой папки. Сам ключ — '
             'в переменной пользователя Windows, не в файле проекта.', T=24, hold=4400),
    dict(cap='«Подготовить OpenCode» собирает надстройку .opencode/opencode.jsonc. Текущая сессия '
             'не переключается: открой новый чат build (после нового ключа — перезапусти Desktop).',
         T=26, hold=4600),
    dict(cap='Поставить задачу можно двумя равными способами: написать ТЗ прямо в чате '
             'или заполнить TASK.md и отправить «Начинай».', T=30, hold=4600),
    dict(cap='Дальше Мастер Чиф сам читает остальные документы, открывает учёт и дашборд '
             'и показывает план — или работает автономно, если ты так разрешил.', T=18, hold=5000),
]

CHIPS = [('1', 'Кит в проекте', (0, 0)), ('2', 'AGENTS.md', (1, 1)), ('3', 'Модели и API', (2, 4)),
         ('4', 'Сохранение', (5, 6)), ('5', 'Задача', (7, 8))]


def chips(c, s):
    x = 30
    for num, label, (a, b) in CHIPS:
        act = a <= s <= b
        done = s > b
        w = c.tlen(label, 15, 's') + 52
        col = BLUE if act else (GREEN if done else BORDER)
        c.rr(x, 74, w, 32, mix(col, 0.22) if act else PANEL, col, 2, 16)
        c.d.ellipse([x + 7, 81, x + 25, 99], fill=col)
        c.t(x + 16, 90, '✓' if done else num, 12, 'b', (255, 255, 255), anchor='mm', bg=col)
        c.t(x + 33, 90, label, 15, 's', TEXT if (act or done) else MUTED, anchor='lm',
            bg=mix(col, 0.22) if act else PANEL)
        x += w + 12


def folder(c, x, y, w, h, title, items, a=1.0, active=False, color=BLUE):
    if active:
        c.glow(x, y, w, h, color, a)
    c.rr(x, y, w, h, PANEL, color if active else BORDER, 3 if active else 2, 12, a)
    c.t(x + 18, y + 14, title, 17, 's', TEXT, a, bg=PANEL)
    for i, (name, col, ai) in enumerate(items):
        yy = y + 52 + i * 34
        aa = a * ai
        c.rr(x + 16, yy, w - 32, 28, PANEL2, None, 0, 6, aa, bg=PANEL)
        c.d.rectangle([x + 26, yy + 9, x + 40, yy + 20], fill=mix(col, aa, PANEL2))
        c.t(x + 50, yy + 14, name, 14, 'm', TEXT, aa, anchor='lm', bg=PANEL2)


KIT = [('opencode.jsonc', BLUE), ('AGENTS.md', BLUE), ('.opencode/commands/', BLUE), ('kit/', BLUE)]


def scene_copy(c, s, p):
    left = [(n, col, 1) for n, col in KIT]
    folder(c, 40, 130, 420, 230, 'Шаблон кита', left, 1, False)
    arrived = [('app/', MUTED, 1), ('tests/', MUTED, 1)]
    for i, (n, col) in enumerate(KIT):
        arrived.append((n, col, seg(p, 0.2 + i * 0.15, 0.32 + i * 0.15)))
    folder(c, 740, 130, 420, 300, 'Мой проект (любой язык)', arrived, 1, True)
    for i, (n, col) in enumerate(KIT):
        t = seg(p, 0.05 + i * 0.15, 0.3 + i * 0.15)
        if 0 < t < 1:
            c.packet([(460, 196 + i * 34), (740, 264 + i * 34)], t, n, BLUE)
    c.rr(40, 450, 1120, 100, PANEL, BORDER, 1, 12)
    c.t(60, 466, 'В .gitignore проекта:', 15, 's', MUTED, bg=PANEL)
    c.t(60, 494, '.opencode/opencode.jsonc   .opencode/kit-models.json   .metrics/', 15, 'm', YELLOW,
        seg(p, 0.75, 0.95), bg=PANEL)
    c.t(60, 522, 'исходный opencode.jsonc с комментариями не переписывается — кит пишет только надстройку',
        14, 'r', MUTED, seg(p, 0.8, 1), bg=PANEL)


AG = [
    ('## Project stack  # EDIT', BLUE),
    ('py kit/task_metrics.py test --task <ID> \\', TEXT),
    ('  --junit-dir target/surefire-reports -- mvn -q test', YELLOW),
    ('', TEXT),
    ('## Project layout  # EDIT', BLUE),
    ('- src/main/java   - src/test/java', TEXT),
    ('', TEXT),
    ('## Work plan (memory)  # EDIT', BLUE),
    ('- Plan file name: currentsteps.md', TEXT),
]


def scene_agents(c, s, p):
    top = c.window(40, 124, 610, 300, 'AGENTS.md', 1, True)
    total = sum(len(t) + 1 for t, _ in AG)
    c.code(60, top + 4, AG, total * seg(p, 0.05, 0.6), 1, 14, 26)
    top2 = c.window(670, 124, 490, 300, 'PowerShell', 1, seg(p, 0.6, 0.7) > 0, GREEN)
    cmd = [('> py kit/task_metrics.py check \\', TEXT),
           ('    --junit-dir target/surefire-reports \\', TEXT),
           ('    -- mvn -q test', TEXT)]
    tot2 = sum(len(t) + 1 for t, _ in cmd)
    c.code(690, top2 + 4, cmd, tot2 * seg(p, 0.6, 0.85), 1, 14, 24)
    c.t(690, top2 + 100, 'CHECK OK', 22, 'mb', GREEN, seg(p, 0.88, 0.95))
    c.t(690, top2 + 134, 'результат тестов читается — можно работать', 14, 'r', MUTED, seg(p, 0.9, 1))
    c.t(690, top2 + 170, 'exit 4 → сначала исправить настройку', 14, 'r', ORANGE, seg(p, 0.92, 1))
    c.rr(40, 440, 1120, 112, PANEL, BORDER, 1, 12)
    c.para(60, 456, 'Читаемый результат: итог Python unittest или JUnit XML (Maven, Gradle, .NET, Vitest, '
                    'Jest, Go, Rust, PHPUnit). Таблица команд для разных языков — в README.', 1080, 16,
           'r', TEXT, seg(p, 0.2, 0.4), bg=PANEL)


SOURCES = [
    ('Локально · LM Studio', 'уже загруженная модель; кит не грузит и не выгружает', GREEN),
    ('Модель из OpenCode', 'подключена через /connect: OpenCode Go, ChatGPT, OpenRouter…', BLUE),
    ('Свой API', 'любой OpenAI-совместимый: адрес …/v1 + ключ + модель', PURPLE),
]


def scene_sources(c, s, p):
    roles = [('Мастер Чиф', 'архитектура, каркас, ревью', BLUE, 170),
             ('Исполнители', 'executor и executor-fast — один выбор', ORANGE, 370)]
    for name, sub, col, y in roles:
        c.node(60, y, 330, 96, name, sub, col, 1, True, tsize=20)
    for i, (name, sub, col) in enumerate(SOURCES):
        y = 130 + i * 140
        a = seg(p, 0.1 + i * 0.15, 0.3 + i * 0.15)
        c.node(760, y, 400, 104, name, sub, col, a, False, tsize=19)
    links = [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
    for k, (r, src) in enumerate(links):
        ry = roles[r][3] + 48
        sy = 130 + src * 140 + 52
        a = seg(p, 0.5 + k * 0.08, 0.6 + k * 0.08)
        c.arrow([(390, ry), (575, ry), (575, sy), (758, sy)], roles[r][2], a, 2, a)
    c.t(60, 540, 'Без файла выбора: Мастер Чиф — из opencode.jsonc, исполнители — загруженная модель LM Studio.',
        15, 'r', MUTED, seg(p, 0.85, 1))


def config_window(c, role, source, a=1.0):
    x, y, w, h = 40, 120, 720, 456
    top = c.window(x, y, w, h, 'Модели проекта — OpenCode Kit', a)
    bw = 222
    tabs = [('Мастер Чиф', 'Архитектура и ревью', BLUE), ('Исполнители', 'Реализация кода', ORANGE),
            ('OpenRouter', 'Каталог и цены', PURPLE)]
    for i, (t1, t2, col) in enumerate(tabs):
        bx = x + 16 + i * (bw + 10)
        act = i == role
        c.rr(bx, top, bw, 54, mix(BLUE, 0.22, PANEL) if act else PANEL2, BLUE if act else BORDER, 2, 8, a, bg=PANEL)
        c.t(bx + 14, top + 8, t1, 15, 's', TEXT, a, bg=PANEL2)
        c.t(bx + 14, top + 30, t2, 13, 'r', MUTED, a, bg=PANEL2)
    opts = ['Из настроек проекта', 'Локально · LM Studio', 'Модель из OpenCode', 'Свой API']
    ox = x + 20
    for i, o in enumerate(opts):
        oy = top + 72
        cx = ox + 8
        sel = i == source
        c.d.ellipse([cx - 7, oy + 3, cx + 7, oy + 17], outline=mix(BLUE if sel else MUTED, a, PANEL), width=2)
        if sel:
            c.d.ellipse([cx - 3, oy + 7, cx + 3, oy + 13], fill=mix(BLUE, a, PANEL))
        c.t(cx + 14, oy + 1, o, 14, 's' if sel else 'r', TEXT if sel else MUTED, a, bg=PANEL)
        ox += c.tlen(o, 14, 's') + 46
    by = y + h - 50
    return top + 110, by


def field(c, x, y, w, label, value, a=1.0, mono=True, active=False):
    c.t(x, y, label, 13, 's', MUTED, a, bg=PANEL)
    c.rr(x, y + 20, w, 32, PANEL2, BLUE if active else BORDER, 2, 6, a, bg=PANEL)
    c.t(x + 10, y + 36, value, 14, 'm' if mono else 'r', TEXT, a, anchor='lm', bg=PANEL2)


def bottom_buttons(c, by, hl=None, click=0.0):
    labels = [('Сохранить настройки', 190), ('Подготовить OpenCode', 200), ('Вернуть по умолчанию', 200)]
    x = 56
    for i, (lab, w) in enumerate(labels):
        c.button(x, by, w, 34, lab, BLUE, 1, filled=i == 0, active=hl == i, size=14)
        x += w + 12


def side_note(c, title, lines, color=BLUE, a=1.0):
    x, y, w, h = 780, 120, 380, 456
    c.rr(x, y, w, h, PANEL, BORDER, 2, 12, a)
    c.t(x + 18, y + 16, title, 17, 's', color, a, bg=PANEL)
    yy = y + 52
    for ln, ai in lines:
        yy = c.para(x + 18, yy, ln, w - 36, 15, 'r', TEXT, a * ai, bg=PANEL) + 10


def scene_mc(c, s, p):
    fy, by = config_window(c, 0, 2)
    field(c, 60, fy, 470, 'Модель OpenCode', 'openai/gpt-6.1-sol'[:int(18 * seg(p, 0.2, 0.6))],
          active=True)
    c.button(546, fy + 20, 150, 32, 'Получить модели', BLUE, 1, size=13)
    c.para(60, fy + 66, 'Подключения, уже известные OpenCode. Полное имя: провайдер/модель.', 660, 14,
           'r', MUTED, bg=PANEL)
    bottom_buttons(c, by)
    side_note(c, 'Мастер Чиф', [
        ('Нужна сильная модель: архитектура, спецификации, ревью.', seg(p, 0.3, 0.5)),
        ('«Модель из OpenCode» — то, что подключено через /connect: OpenCode Go, подписка ChatGPT, '
         'OpenRouter и др.', seg(p, 0.45, 0.65)),
        ('Для своего сервиса — вариант «Свой API».', seg(p, 0.6, 0.8)),
    ])


def scene_exec(c, s, p):
    fy, by = config_window(c, 1, 3)
    url = 'https://api.example.com/v1'
    field(c, 60, fy, 470, '1. Адрес API', url[:int(len(url) * seg(p, 0.05, 0.25))], active=p < 0.27)
    c.button(546, fy + 20, 150, 32, 'Проверить связь', GREEN, 1, size=13, active=0.42 <= p < 0.56)
    field(c, 60, fy + 64, 636, '2. API-ключ', '•' * int(24 * seg(p, 0.27, 0.4)),
          active=0.27 <= p < 0.42)
    model = 'coder-model-large' if p > 0.9 else ''
    field(c, 60, fy + 128, 470, '3. Модель', model, active=p >= 0.58)
    c.button(546, fy + 148, 150, 32, 'Получить модели', BLUE, 1, size=13, active=0.58 <= p < 0.8)
    if 0.66 < p < 0.92:
        a = seg(p, 0.66, 0.7)
        c.rr(60, fy + 182, 470, 96, PANEL2, BLUE, 2, 6, a, bg=PANEL)
        for i, m in enumerate(['coder-model-small', 'coder-model-large', 'general-model']):
            if i == 1 and p > 0.8:
                c.rr(64, fy + 186 + i * 30, 462, 28, mix(BLUE, 0.35, PANEL2), None, 0, 4, a, bg=PANEL2)
            c.t(76, fy + 200 + i * 30, m, 14, 'm', TEXT, a, anchor='lm', bg=PANEL2)
    if p > 0.92:
        c.t(60, fy + 196, 'Получено моделей: 3. Выбери модель из списка.', 14, 'r', GREEN, bg=PANEL)
    if p < 0.58:
        cx, cy = 620, fy + 36
    elif p < 0.8:
        cx, cy = 620, fy + 36 + 128 * seg(p, 0.56, 0.6)
    else:
        cx, cy = 620 - 300 * seg(p, 0.78, 0.82), fy + 164 + 60 * seg(p, 0.78, 0.82)
    click = seg(p, 0.44, 0.52) if p < 0.56 else (seg(p, 0.6, 0.66) if p < 0.8 else seg(p, 0.83, 0.88))
    c.cursor((cx, cy), seg(p, 0.38, 0.42) * (1 - seg(p, 0.92, 0.95)), click=click)
    bottom_buttons(c, by)
    side_note(c, 'Исполнители', [
        ('Адрес — базовый, без /chat/completions и /models.', seg(p, 0.1, 0.25)),
        ('Ключ скрыт маской. Если он уже сохранён, окно пишет «Ключ найден» — вводить заново не нужно.',
         seg(p, 0.3, 0.42)),
        ('«Проверить связь»: API доступен. Генерация не запускается, ничего не сохраняется.',
         seg(p, 0.5, 0.58)),
        ('«Получить модели» заполняет список; имя можно ввести и вручную.', seg(p, 0.7, 0.85)),
    ], ORANGE)


def scene_save(c, s, p):
    fy, by = config_window(c, 1, 3)
    field(c, 60, fy, 636, '1. Адрес API', 'https://api.example.com/v1')
    field(c, 60, fy + 64, 636, '2. API-ключ', '•' * 24)
    field(c, 60, fy + 128, 470, '3. Модель', 'coder-model-large')
    bottom_buttons(c, by, hl=0 if p > 0.15 else None)
    c.cursor((150, by + 18), seg(p, 0, 0.1) * (1 - seg(p, 0.5, 0.55)), click=seg(p, 0.15, 0.3))
    x, y, w = 780, 120, 380
    a = seg(p, 0.3, 0.45)
    top = c.window(x, y, w, 250, '.opencode/kit-models.json', a, True, GREEN)
    js = [('{', MUTED), ('  "masterChief": {', TEXT), ('    "source": "opencode",', TEXT),
          ('    "model": "openai/gpt-6.1-sol" },', TEXT), ('  "executors": {', TEXT),
          ('    "source": "api",', TEXT), ('    "baseURL": "https://api.example.com/v1",', TEXT),
          ('    "model": "coder-model-large",', TEXT), ('    "keyEnv": "OCK_EXECUTORS_API_KEY" }', YELLOW),
          ('}', MUTED)]
    c.code(x + 14, top - 2, js, None, a, 12, 19)
    a2 = seg(p, 0.6, 0.75)
    c.rr(x, 384, w, 192, PANEL, YELLOW, 2, 12, a2)
    c.t(x + 18, 398, 'Переменная пользователя Windows', 16, 's', YELLOW, a2, bg=PANEL)
    c.t(x + 18, 430, 'OCK_EXECUTORS_API_KEY = ••••••••', 14, 'm', TEXT, a2, bg=PANEL)
    c.para(x + 18, 462, 'В файле проекта — только имя переменной. Папки с одним именем переменной '
                        'используют один ключ. Ключ не отправляется в чат.', w - 36, 14, 'r', MUTED, a2,
           bg=PANEL)


def scene_prepare(c, s, p):
    fy, by = config_window(c, 1, 3, 0.55)
    bottom_buttons(c, by, hl=1 if p > 0.12 else None)
    c.cursor((350, by + 18), seg(p, 0, 0.08) * (1 - seg(p, 0.35, 0.4)), click=seg(p, 0.1, 0.25))
    steps = [('kit-models.json', 'выбор ролей', GREEN),
             ('run_opencode.py --prepare-only', 'собирает настройки', BLUE),
             ('.opencode/opencode.jsonc', 'надстройка поверх исходного конфига', PURPLE),
             ('Новый чат build', 'после нового ключа — перезапуск Desktop', ORANGE)]
    for i, (t1, t2, col) in enumerate(steps):
        y = 124 + i * 112
        a = seg(p, 0.25 + i * 0.15, 0.38 + i * 0.15)
        c.node(800, y, 360, 86, t1, t2, col, a, active=a > 0 and i == 3, tsize=16, ssize=13)
        if i:
            c.arrow([(980, y - 26), (980, y - 2)], col, a, 3, a)


def scene_two_ways(c, s, p):
    # lane A
    c.t(40, 128, 'Способ А · ТЗ в чате', 17, 'b', GREEN)
    ax, ay, aw, ah = 40, 158, 560, 120
    a = seg(p, 0.0, 0.15)
    c.rr(ax, ay, aw, ah, PANEL2, GREEN, 2, 14, a)
    msg = '«Добавь учёт расходов: сумма, категория и дата. Отрицательную сумму принимать нельзя. Сначала покажи план.»'
    msg = tr(msg)
    c.para(ax + 18, ay + 16, msg[:int(len(msg) * seg(p, 0.05, 0.45))], aw - 36, 16, 'r', TEXT, a, bg=PANEL2)
    # lane B
    c.t(40, 310, 'Способ Б · TASK.md + «Начинай»', 17, 'b', YELLOW)
    b = seg(p, 0.45, 0.6)
    top = c.window(40, 340, 380, 190, 'TASK.md', b, False, YELLOW)
    tl = [('# Домашний бюджет', BLUE), ('- покупки: продукт, кол-во, цена', TEXT),
          ('- остатки дома, расходы недели', TEXT), ('## Критерии приёмки', BLUE),
          ('- данные сохраняются между запусками', TEXT)]
    c.code(56, top, tl, None, b, 13, 26)
    c.rr(440, 420, 160, 54, PANEL2, YELLOW, 2, 14, seg(p, 0.6, 0.7))
    c.t(520, 447, '«Начинай»', 17, 's', TEXT, seg(p, 0.6, 0.7), anchor='mm', bg=PANEL2)
    # master chief
    mx, my = 820, 300
    c.node(mx, my, 330, 104, 'Мастер Чиф', 'читает требования и сам находит остальное', BLUE, 1,
           active=True, tsize=20)
    c.arrow([(ax + aw, ay + ah / 2), (720, ay + ah / 2), (720, my + 30), (mx - 2, my + 30)], GREEN,
            seg(p, 0.4, 0.5), 3, seg(p, 0.4, 0.55))
    c.arrow([(600, 447), (720, 447), (720, my + 74), (mx - 2, my + 74)], YELLOW,
            seg(p, 0.7, 0.75), 3, seg(p, 0.7, 0.85))
    c.para(820, 430, 'Явное сообщение в чате важнее файла. TASK.md без просьбы не перезаписывается. '
                     'Открытие папки само по себе работу не запускает.', 340, 14, 'r', MUTED,
           seg(p, 0.85, 1))


def scene_go(c, s, p):
    c.node(60, 250, 320, 110, 'Мастер Чиф', 'задача принята', BLUE, 1, True, tsize=21)
    outs = [('Читает сам', 'AGENTS.md · currentsteps.md · README · архитектура', PURPLE),
            ('task_metrics start', 'учёт задачи + дашборд открывается автоматически', GREEN),
            ('План в currentsteps.md', 'модули, интерфейсы, порядок', BLUE),
            ('Утверждение', 'показывает план — или идёт дальше, если ты разрешил всю задачу', ORANGE)]
    for i, (t1, t2, col) in enumerate(outs):
        y = 124 + i * 112
        a = seg(p, 0.1 + i * 0.18, 0.25 + i * 0.18)
        c.node(560, y, 600, 88, t1, t2, col, a, tsize=18)
        c.arrow([(380, 305), (470, 305), (470, y + 44), (558, y + 44)], col, a, 2, a)


SCENES = [scene_copy, scene_agents, scene_sources, scene_mc, scene_exec, scene_save, scene_prepare,
          scene_two_ways, scene_go]


def draw(c, s, p):
    chips(c, s)
    SCENES[s](c, s, p)


if __name__ == '__main__':
    n = build('../03_project_setup.gif', STEPS, draw, 'GIF 3/5', 'Настройка проекта под новую задачу')
    print('frames', n)
