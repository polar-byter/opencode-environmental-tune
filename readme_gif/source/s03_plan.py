"""GIF 3: how the Master Chief prepares the work."""
from gifkit import *

STEPS = [
    dict(cap='Задачу можно написать прямо в чате — или в файле TASK.md и отправить «Начинай». '
             'Если они расходятся, главнее чат.', T=18, hold=4400),
    dict(cap='Мастер Чиф сам читает нужное: правила кита, план прошлых сессий и то, что уже есть в проекте.',
         T=18, hold=4400),
    dict(cap='Решает, из каких частей будет программа и в каком порядке. Заранее фиксирует договорённости '
             'между частями.', T=20, hold=4600),
    dict(cap='Пишет заготовки: названия функций и подробное описание, что каждая делает. '
             'Внутри — пометка «TODO: executor».', T=30, hold=4600),
    dict(cap='Сразу пишет тесты. Пока функции пустые, тесты не проходят.', T=22, hold=4400),
    dict(cap='Открывает учёт задачи — дашборд запускается сам. План записан в currentsteps.md.',
         T=16, hold=4800),
]

STAGES = ['Задача', 'Чтение', 'Решения', 'Заготовки', 'Тесты', 'Старт']


def stages(c, s):
    x = 40
    for i, lab in enumerate(STAGES):
        act, done = i == s, i < s
        col = BLUE if act else (GREEN if done else BORDER)
        w = 172
        c.rr(x, 78, w, 40, mix(col, 0.22) if act else PANEL, col, 2, 20)
        c.t(x + w / 2, 98, ('✓ ' if done else '') + tr(lab), 16, 's', TEXT if (act or done) else MUTED,
            anchor='mm', bg=mix(col, 0.22) if act else PANEL)
        if i < len(STAGES) - 1:
            c.t(x + w + 9, 98, '→', 16, 'r', DIM, anchor='mm')
        x += w + 18


SKELETON = [
    ('class Budget:', BLUE),
    ('    def add_purchase(self, product, qty, price):', BLUE),
    ('        """Save a purchase and return its id.', GREEN),
    ('        qty <= 0 or price < 0 -> ValueError"""', GREEN),
    ('        raise NotImplementedError("TODO: executor")', ORANGE),
]


def draw(c, s, p):
    stages(c, s)
    if s == 0:
        a = seg(p, 0.05, 0.3)
        c.rr(60, 160, 520, 220, PANEL2, GREEN, 2, 18, a)
        c.t(84, 182, 'В чате', 18, 's', GREEN, a, bg=PANEL2)
        msg = tr('«Сделай домашний бюджет: покупки по продуктам, остатки дома и расходы за неделю. '
                 'Сначала покажи план.»')
        n = int(len(msg) * seg(p, 0.1, 0.7))
        c.para(84, 218, msg[:n], 470, 18, 'r', TEXT, a, bg=PANEL2)
        b = seg(p, 0.5, 0.75)
        c.t(620, 270, 'или', 20, 's', MUTED, b, anchor='mm')
        top = c.window(660, 160, 480, 220, 'TASK.md', b, False, YELLOW)
        c.code(680, top + 4, [('# Домашний бюджет', BLUE), ('- покупки, остатки, расходы', TEXT),
                              ('## Критерии приёмки', BLUE), ('- данные не теряются', TEXT)], None, b, 16, 30)
        c.rr(800, 400, 200, 50, PANEL2, YELLOW, 2, 14, b)
        c.t(900, 425, '«Начинай»', 18, 's', TEXT, b, anchor='mm', bg=PANEL2)
    elif s == 1:
        docs = [('AGENTS.md', 'правила работы', BLUE), ('currentsteps.md', 'план и память между сессиями', PURPLE),
                ('README и код', 'что уже есть в проекте', CYAN)]
        for i, (t1, t2, col) in enumerate(docs):
            a = seg(p, 0.05 + i * 0.2, 0.3 + i * 0.2)
            x = 60 + i * 370
            c.rr(x, 170, 340, 200, PANEL, col, 2, 16, a)
            c.pageicon(x + 24, 196, col, a, s=1.8)
            c.t(x + 24, 268, t1, 22, 's', TEXT, a, bg=PANEL)
            c.para(x + 24, 302, t2, 290, 16, 'r', MUTED, a, bg=PANEL)
        c.t(600, 430, 'перечислять документы не нужно — он находит их сам', 18, 'r', MUTED,
            seg(p, 0.75, 0.95), anchor='mm')
    elif s == 2:
        items = [('Части и порядок', 'сначала данные, потом логика, потом экран'),
                 ('Договорённости', 'интерфейсы, общие типы, схема базы данных'),
                 ('Размер поручения', 'один небольшой файл или класс')]
        for i, (t1, t2) in enumerate(items):
            a = seg(p, 0.05 + i * 0.22, 0.3 + i * 0.22)
            card(c, 160, 150 + i * 135, 880, 115, t1, t2, BLUE, a, badge=str(i + 1), tsize=22, ssize=17)
    elif s == 3:
        top = c.window(80, 150, 760, 260, 'app/budget.py', 1, True)
        tot = sum(len(t) + 1 for t, _ in SKELETON)
        c.code(104, top + 8, SKELETON, tot * seg(p, 0.05, 0.85), 1, 17, 32)
        card(c, 870, 170, 290, 200, 'Зачем так', 'слабой модели не нужно придумывать — только сделать по описанию',
             ORANGE, seg(p, 0.6, 0.85), tsize=19, ssize=15)
    elif s == 4:
        top = c.window(80, 150, 760, 260, 'tests/test_budget.py', 1, True, RED)
        tests = ['test_add_purchase_returns_id', 'test_negative_price_rejected', 'test_zero_qty_rejected']
        for i, t in enumerate(tests):
            a = seg(p, 0.1 + i * 0.18, 0.25 + i * 0.18)
            c.t(104, top + 12 + i * 44, t, 18, 'm', TEXT, a, bg=PANEL)
            c.t(810, top + 12 + i * 44, 'FAIL', 18, 'mb', RED, a, anchor='ra', bg=PANEL)
        card(c, 870, 170, 290, 200, 'Это нормально', 'тесты описывают, что должно получиться', GREEN,
             seg(p, 0.7, 0.9), tsize=19, ssize=15)
    else:
        card(c, 80, 170, 480, 140, 'Учёт задачи открыт', 'время и токены не смешаются с прошлой работой',
             GREEN, seg(p, 0.05, 0.3), badge='▣', tsize=21, ssize=16)
        card(c, 80, 340, 480, 140, 'План записан', 'currentsteps.md — к нему можно вернуться завтра',
             PURPLE, seg(p, 0.25, 0.5), badge='✓', tsize=21, ssize=16)
        a = seg(p, 0.45, 0.7)
        c.arrow([(560, 240), (640, 240)], CYAN, a, 4, a)
        top = c.window(650, 160, 510, 330, '127.0.0.1 · дашборд', a, True, CYAN)
        c.t(674, top + 10, 'OpenCode · наблюдение за задачей', 18, 'b', TEXT, a, bg=PANEL)
        c.rr(674, top + 50, 460, 70, PANEL2, None, 0, 10, a, bg=PANEL)
        c.t(690, top + 64, 'Статус', 14, 'r', MUTED, a, bg=PANEL2)
        c.t(690, top + 86, 'план готов', 20, 's', TEXT, a, bg=PANEL2)
        c.rr(674, top + 134, 460, 70, PANEL2, None, 0, 10, a, bg=PANEL)
        c.t(690, top + 148, 'Функции', 14, 'r', MUTED, a, bg=PANEL2)
        c.bar(690, top + 176, 420, 14, 0, GREEN, a, PANEL2)
        c.t(674, top + 222, 'открылся сам — команды вводить не нужно', 15, 'r', MUTED, a, bg=PANEL)


NUM, TITLE = 'GIF 3/8', 'Как Мастер Чиф готовит работу'

if __name__ == '__main__':
    print('frames', build('../03_plan.gif', STEPS, draw, NUM, TITLE))
