"""GIF 1: how the Master Chief reads documents, decides and builds the skeleton."""
from gifkit import *

STEPS = [
    dict(cap='Мастер Чиф (агент build) сам находит и читает нужные документы. '
             'От пользователя нужна только задача.', hold=3200),
    dict(cap='Задача приходит прямо из чата — или из TASK.md по короткому «Начинай». '
             'Текущее сообщение в чате важнее файла.', T=22, hold=3400),
    dict(cap='TASK.md — требования и критерии приёмки, не план реализации. '
             'Пустой или старый файл не мешает задаче из чата.', T=12, hold=3600),
    dict(cap='AGENTS.md — правила кита: порядок работы, стек и команда тестов, '
             'где лежит план, что можно поручать исполнителю.', T=12, hold=3800),
    dict(cap='find_vault.py находит Obsidian Vault → currentsteps.md: что уже сделано, '
             'принятые решения и следующий шаг. Это память между сессиями.', T=12, hold=3800),
    dict(cap='README, ARCHITECTURE.md и сам код — чтобы новое решение вписалось '
             'в существующую архитектуру.', T=12, hold=3400),
    dict(cap='LOCAL_MODELS и METRICS читаются по мере надобности: перед настройкой '
             'моделей и перед учётом задачи.', T=12, hold=3400),
    dict(cap='Решения: модули и их интерфейсы, зависимости и порядок, одно задание '
             'исполнителю — небольшой класс целиком. План записан в currentsteps.md.',
         T=24, hold=4200),
    dict(cap='task_metrics start открывает учёт задачи и сам запускает дашборд. '
             'Время и токены этой задачи не смешаются с прошлой работой.', T=12, hold=3600),
    dict(cap='Каркас: классы, сигнатуры и все импорты, подробная спецификация в каждой '
             'функции, а вместо тела — заглушка «TODO: executor».', T=40, hold=4200),
    dict(cap='Тесты пишутся сразу по спецификации. Красный результат ожидаем: '
             'один baseline-прогон фиксирует его до начала работы.', T=24, hold=4200),
    dict(cap='Готово к передаче: требования, план, каркас и красные тесты. '
             'Тела функций Мастер Чиф не пишет — их заполняет исполнитель (GIF 2).', hold=4800),
]

DOCS = [
    ('TASK.md', 'требования и критерии приёмки (необязателен)', YELLOW),
    ('AGENTS.md', 'правила кита, стек, команда тестов', BLUE),
    ('currentsteps.md', 'Obsidian: план, решения, где остановились', PURPLE),
    ('README · ARCHITECTURE', 'как проект устроен сейчас + код', CYAN),
    ('LOCAL_MODELS · METRICS', 'перед настройкой моделей и учётом', MUTED),
]
DX, DW, DH = 30, 300, 74
MC = (420, 240, 230, 112)

SKELETON = [
    ('class ExpenseService:', BLUE),
    ('    def add(self, amount, category, day):', BLUE),
    ('        """Add an expense, return its id.', GREEN),
    ('        amount <= 0     -> ValueError (first)', GREEN),
    ('        empty category  -> ValueError', GREEN),
    ('        """', GREEN),
    ('        raise NotImplementedError("TODO: executor")', ORANGE),
]
TESTS = [
    ('test_add_returns_id', 'FAIL'),
    ('test_negative_amount_rejected', 'FAIL'),
    ('test_empty_category_rejected', 'FAIL'),
]


def doc_y(i):
    return 88 + i * 86


def draw(c, s, p):
    mx, my, mw, mh = MC
    # Master Chief
    c.node(mx, my, mw, mh, 'Мастер Чиф', 'агент build: планирует, пишет каркас и тесты, проверяет',
           BLUE, 1.0, active=s >= 1 and s not in (11,), tsize=21)

    # user request bubble
    a = appear(s, 1, p)
    if a:
        bx, by, bw, bh = 380, 80, 310, 120
        c.rr(bx, by, bw, bh, PANEL2, GREEN if s == 1 else BORDER, 2, 14, a)
        c.t(bx + 14, by + 10, 'Пользователь', 14, 's', GREEN, a, bg=PANEL2)
        msg = '«Добавь учёт расходов: сумма, категория, дата. Отрицательную сумму не принимать.»'
        n = len(msg) if s > 1 else int(len(msg) * seg(p, 0.1, 0.75))
        c.para(bx + 14, by + 32, msg[:n], bw - 28, 14, 'r', TEXT, a, lh=1.3, bg=PANEL2)
        if s >= 1:
            c.t(bx + 14, by + bh - 22, 'или: TASK.md + «Начинай»', 13, 'r', MUTED,
                a * (seg(p, 0.75, 1.0) if s == 1 else 1), bg=PANEL2)
        c.arrow([(535, by + bh), (535, my - 2)], GREEN, a, prog=seg(p, 0.75, 1) if s == 1 else 1)

    # documents
    for i, (name, sub, col) in enumerate(DOCS):
        y = doc_y(i)
        k = i + 2
        act = s == k
        tag = None
        if i == 2 and s >= 7:
            tag = ('план обновлён', GREEN)
        c.doc(DX, y, DW, DH, name, sub, col, 1.0 if s >= k else 0.35, active=act or (i == 2 and s == 7),
              tag=tag)
        # reading line
        if s >= k:
            pts = [(DX + DW, y + DH / 2), (mx - 2, my + mh / 2)]
            prog = seg(p, 0.0, 0.6) if s == k else 1
            c.arrow(pts, col if act else BORDER, 1.0, 2, prog, head=True)
            if act:
                c.dot(c.point_on(pts, seg(p, 0.05, 0.9))[0], col, 6)
    if s == 4:
        c.tag(DX + 150, doc_y(2) - 11, 'find_vault.py', PURPLE, seg(p, 0, 0.3))

    # decisions panel
    a = appear(s, 7, p)
    px, py, pw, ph = 720, 80, 455, 158
    if a:
        c.rr(px, py, pw, ph, PANEL, BLUE if s == 7 else BORDER, 3 if s == 7 else 2, 12, a)
        c.t(px + 18, py + 12, 'Решения Мастер Чифа', 17, 's', TEXT, a, bg=PANEL)
        items = ['модули и публичные интерфейсы', 'зависимости → порядок модулей',
                 '1 задание = небольшой класс целиком', 'план и решения → currentsteps.md']
        for j, it in enumerate(items):
            aj = a * (seg(p, 0.15 + j * 0.18, 0.3 + j * 0.18) if s == 7 else 1)
            yy = py + 44 + j * 27
            c.d.ellipse([px + 20, yy + 6, px + 28, yy + 14], fill=mix(BLUE, aj, PANEL))
            c.t(px + 38, yy, it, 16, 'r', TEXT, aj, bg=PANEL)
        c.arrow([(mx + mw, my + 30), (706, my + 30), (706, py + ph / 2), (px - 2, py + ph / 2)],
                BLUE if s == 7 else BORDER, a, 2, seg(p, 0, 0.3) if s == 7 else 1)

    # task_metrics start
    a = appear(s, 8, p)
    if a:
        c.node(400, 420, 270, 84, 'task_metrics start', 'учёт задачи · дашборд открывается сам',
               GREEN, a, active=s == 8, tsize=17, ssize=13)
        c.arrow([(535, my + mh), (535, 418)], GREEN if s == 8 else BORDER, a, 2,
                seg(p, 0, 0.4) if s == 8 else 1)
        if s >= 8:
            c.tag(668, 408, '→ дашборд', GREEN, a, right=True)

    # skeleton code
    a = appear(s, 9, p)
    kx, ky, kw, kh = 720, 252, 455, 180
    if a:
        top = c.window(kx, ky, kw, kh, 'app/expense_service.py — каркас', a, active=s == 9)
        total = sum(len(t) + 1 for t, _ in SKELETON)
        ch = total * seg(p, 0.1, 0.95) if s == 9 else None
        c.code(kx + 16, top, SKELETON, ch, a, 13, 19)
        c.arrow([(mx + mw, my + 60), (698, my + 60), (698, ky + kh / 2), (kx - 2, ky + kh / 2)],
                BLUE if s == 9 else BORDER, a, 2, seg(p, 0, 0.2) if s == 9 else 1)

    # tests
    a = appear(s, 10, p)
    tx, ty, tw, th = 720, 444, 455, 132
    if a:
        top = c.window(tx, ty, tw, th, 'tests/test_expense_service.py', a, active=s == 10, color=RED)
        for j, (name, res) in enumerate(TESTS):
            aj = a * (seg(p, 0.1 + j * 0.2, 0.25 + j * 0.2) if s == 10 else 1)
            yy = top + j * 21
            c.t(tx + 16, yy, name, 13, 'm', TEXT, aj)
            c.t(tx + tw - 18, yy, res, 13, 'mb', RED, aj, anchor='ra')
        ab = a * (seg(p, 0.8, 1) if s == 10 else 1)
        c.t(tx + 16, top + 66, 'baseline: 0 из 3 — ожидаемо красные', 13, 'm', YELLOW, ab)
        c.arrow([(mx + mw, my + 90), (690, my + 90), (690, ty + th / 2), (tx - 2, ty + th / 2)],
                RED if s == 10 else BORDER, a, 2, seg(p, 0, 0.2) if s == 10 else 1)

    if s == 11:
        c.tag(mx + mw / 2 - 70, my - 11, 'не пишет тела функций', ORANGE, seg(p, 0, 0.4))


if __name__ == '__main__':
    n = build('../01_master_chief_planning.gif', STEPS, draw, 'GIF 1/5',
              'Как Мастер Чиф планирует: документы → решения → каркас и тесты')
    print('frames', n)
