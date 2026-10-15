"""GIF 2: delegation to the executor, inspection, review and the dashboard."""
from gifkit import *

STEPS = [
    dict(cap='Три участника: Мастер Чиф решает и проверяет, исполнитель пишет тела функций, '
             'task_metrics.py ведёт журнал. Дашборд показывает всё вживую.', hold=3600),
    dict(cap='Перед вызовом требования записываются в .metrics/<ID>/<work_item>-requirements.json: '
             'каждый пограничный случай, порядок проверок, инварианты.', T=18, hold=3800),
    dict(cap='Архитектура и реестр функций публикуются в дашборд (dashboard.tracking) — '
             'появляется общий счёт функций задачи.', T=16, hold=3400),
    dict(cap='delegate замораживает требования и делает снимок хешей всех файлов проекта, '
             'включая новые и игнорируемые Git. Выдаётся delegation_id.', T=16, hold=3800),
    dict(cap='Исполнитель получает один файл со спецификациями и свой progress-файл. '
             'Заполняет только тела функций, отмечая текущую функцию — дашборд видит прогресс.',
         T=40, hold=4200),
    dict(cap='Сразу после ответа — inspect, до любых правок и тестов. Изменён чужой файл → '
             'exit 1 и возврат. Здесь границы соблюдены.', T=16, hold=3800),
    dict(cap='Ревью по каждому требованию: место в коде + тест. Мастер Чиф дописал тест '
             'на пустую категорию — он упал. Зелёных тестов недостаточно.', T=22, hold=4400),
    dict(cap='review --result rework: один возврат, даже если замечаний несколько. '
             'Новая попытка снова регистрируется через delegate.', T=26, hold=4000),
    dict(cap='Вторая попытка: inspect чист, тесты области зелёные, каждое требование '
             'подтверждено → review --result accepted. Функции становятся «принятыми».',
         T=26, hold=4400),
    dict(cap='Защита от зацикливания: при срабатывании лимита task_metrics возвращает '
             'exit 3 STOP — Мастер Чиф останавливается и ждёт решения пользователя.', T=14, hold=4600),
    dict(cap='В конце обязателен полный прогон --scope full, затем finish: отчёт со временем, '
             'возвратами, прогонами и токенами по группам моделей.', T=22, hold=5200),
]

MC = (30, 84, 250, 96)
TM = (475, 84, 250, 96)
EX = (920, 84, 250, 96)
CARD_Y, CARD_H = 204, 214
LC = (30, CARD_Y, 365, CARD_H)
CC = (418, CARD_Y, 365, CARD_H)
RC = (806, CARD_Y, 364, CARD_H)
DASH = (30, 432, 1140, 140)

REQS = ['amount <= 0 → ValueError, раньше всего', 'пустая категория → ValueError',
        'add возвращает id новой записи']

CODE1 = [
    ('def add(self, amount, category, day):', BLUE),
    ('    if amount <= 0:', TEXT),
    ('        raise ValueError("amount")', TEXT),
    ('    self._items.append(...)', TEXT),
    ('    return len(self._items)', TEXT),
]
CODE2 = [
    ('def add(self, amount, category, day):', BLUE),
    ('    if amount <= 0:', TEXT),
    ('        raise ValueError("amount")', TEXT),
    ('    if not category:', GREEN),
    ('        raise ValueError("category")', GREEN),
    ('    self._items.append(...)', TEXT),
    ('    return len(self._items)', TEXT),
]


def center(box, side):
    x, y, w, h = box
    return {'l': (x, y + h / 2), 'r': (x + w, y + h / 2), 't': (x + w / 2, y), 'b': (x + w / 2, y + h)}[side]


def card(c, box, title, lines, a, accent=BORDER, active=False, reveal=None):
    """lines: list of (text, color[, size])."""
    if a <= 0:
        return
    x, y, w, h = box
    if active:
        c.glow(x, y, w, h, accent, a)
    c.rr(x, y, w, h, PANEL, accent if active else BORDER, 3 if active else 2, 12, a)
    c.t(x + 16, y + 12, title, 15, 's', accent if accent != BORDER else MUTED, a, bg=PANEL)
    yy = y + 40
    for i, ln in enumerate(lines):
        text, col = ln[0], ln[1]
        size = ln[2] if len(ln) > 2 else 14
        ai = a * (reveal(i) if reveal else 1)
        font = 'm' if size == 13 else 'r'
        c.t(x + 16, yy, text, size, font, col, ai, bg=PANEL)
        yy += 22 if size >= 14 else 20


def dash_state(s, p):
    st = dict(status='выполняется', scol=BLUE, deleg=0, acc='0/1', rew=0, runs='0/0',
              impl=0, accd=0, total=None, now='—')
    if s >= 2:
        st['total'] = 3
    if s >= 3:
        st['deleg'] = 1
    if s == 4:
        st['impl'] = min(3, int(seg(p, 0.15, 0.95) * 3.999))
        names = ['add', 'add', 'total_for_week', 'remaining']
        st['now'] = tr('исполнитель · ExpenseService · ') + names[min(3, int(seg(p, 0.1, 0.95) * 3.999))]
    if s >= 5:
        st['impl'] = 3
        st['now'] = 'Мастер Чиф · ревью ExpenseService'
    if s >= 6:
        st['runs'] = '0/1'
    if s >= 7:
        st['rew'] = 1
        st['impl'] = 0
        st['deleg'] = 2
        st['now'] = 'исполнитель · ExpenseService · попытка 2'
    if s == 7:
        st['impl'] = int(seg(p, 0.5, 0.95) * 3)
    if s >= 8:
        st['impl'] = 3
        st['accd'] = 3 if (s > 8 or p > 0.7) else 0
        st['acc'] = '1/1' if (s > 8 or p > 0.7) else '0/1'
        st['runs'] = '1/2' if (s > 8 or p > 0.5) else '0/1'
        st['now'] = 'Мастер Чиф · следующий модуль'
    if s == 9:
        st['status'], st['scol'] = 'STOP · ждёт решения', RED
        st['now'] = 'пример: лимит возвратов исчерпан'
    if s >= 10:
        st['runs'] = '2/3' if p > 0.3 else '1/2'
        if p > 0.6:
            st['status'], st['scol'] = '✓ Работа завершена', GREEN
            st['now'] = 'итоговый отчёт готов'
    return st


def draw_dash(c, s, p):
    x, y, w, h = DASH
    st = dash_state(s, p)
    active = s in (2, 3, 4, 7, 8, 10)
    if active:
        c.glow(x, y, w, h, CYAN, 0.6)
    c.rr(x, y, w, h, PANEL, CYAN if active else BORDER, 2, 12)
    c.t(x + 16, y + 10, 'Дашборд', 16, 'b', CYAN, bg=PANEL)
    c.t(x + 30 + c.tlen('Дашборд', 16, 'b'), y + 12, '127.0.0.1 · expenses-20261015 · обновление каждые 2 с', 13, 'r', MUTED, bg=PANEL)
    sw = c.tlen(st['status'], 13, 's') + 20
    c.rr(x + w - sw - 16, y + 9, sw, 24, mix(st['scol'], 0.25, PANEL), st['scol'], 1, 12, bg=PANEL)
    c.t(x + w - 16 - sw / 2, y + 21, st['status'], 13, 's', st['scol'], anchor='mm',
        bg=mix(st['scol'], 0.25, PANEL))
    tiles = [('Задания исполнителю', str(st['deleg'])), ('Задания приняты', st['acc']),
             ('Возвраты на доработку', str(st['rew'])), ('Успешные прогоны / все', st['runs'])]
    tw = 196
    for i, (lab, val) in enumerate(tiles):
        tx = x + 16 + i * (tw + 10)
        c.rr(tx, y + 42, tw, 56, PANEL2, None, 0, 8, bg=PANEL)
        c.t(tx + 12, y + 48, lab, 12, 'r', MUTED, bg=PANEL2)
        col = RED if (lab.startswith('Возвраты') and st['rew']) else TEXT
        c.t(tx + 12, y + 64, val, 22, 'b', col, bg=PANEL2)
    fx = x + 16 + 4 * (tw + 10)
    fw = w - (fx - x) - 16
    c.rr(fx, y + 42, fw, 56, PANEL2, None, 0, 8, bg=PANEL)
    c.t(fx + 12, y + 48, 'Функции: заявлено / принято', 12, 'r', MUTED, bg=PANEL2)
    if st['total']:
        c.t(fx + fw - 12, y + 48, tr("{a} / {b} из {c}").format(a=st['impl'], b=st['accd'], c=st['total']), 12, 's', TEXT,
            anchor='ra', bg=PANEL2)
        c.bar(fx + 12, y + 74, fw - 24, 12, st['accd'] / 3, GREEN, 1, PANEL2, st['impl'] / 3, mix(BLUE, 0.6, PANEL2))
    else:
        c.t(fx + 12, y + 68, 'реестр не опубликован', 13, 'r', DIM, bg=PANEL2)
    c.t(x + 16, y + 110, 'Сейчас в работе:', 14, 's', MUTED, bg=PANEL)
    c.t(x + 140, y + 110, st['now'], 14, 'r', TEXT, bg=PANEL)


def draw(c, s, p):
    c.node(*MC, 'Мастер Чиф', 'требования, ревью, тесты', BLUE, active=s in (1, 6, 7, 8, 9))
    c.node(*TM, 'task_metrics.py', 'журнал, снимки, тесты, лимиты', PURPLE, active=s in (3, 5, 9, 10))
    c.node(*EX, 'Исполнитель', 'LM Studio · OpenRouter · свой API', ORANGE, active=s in (4, 7, 8))

    mc_r, tm_l, tm_r, ex_l = center(MC, 'r'), center(TM, 'l'), center(TM, 'r'), center(EX, 'l')
    c.arrow([mc_r, tm_l], BORDER, 1, 2, head=True)
    route_ex = [(MC[0] + MC[2] - 40, MC[1] + MC[3]), (MC[0] + MC[2] - 40, 192), (EX[0] + 40, 192),
                (EX[0] + 40, EX[1] + EX[3])]
    c.arrow(route_ex, BORDER, 1, 2, head=True)

    # left card: requirements → checks
    if s >= 1:
        a = appear(s, 1, p)
        if s < 6:
            card(c, LC, 'GameService…  →  ExpenseService-requirements.json'[0:0] + 'requirements.json',
                 [('[', MUTED, 13)] + [('  "' + tr(r) + '",', YELLOW, 13) for r in REQS] + [(']', MUTED, 13)],
                 a, YELLOW, active=s == 1,
                 reveal=(lambda i: seg(p, 0.1 + i * 0.12, 0.25 + i * 0.12)) if s == 1 else None)
        else:
            if s == 6:
                marks = [('✓', GREEN), ('✗', RED), ('✓', GREEN)]
                title, acc = 'checks.json — ревью', RED
            else:
                ok = s >= 8 and (s > 8 or p > 0.55)
                marks = [('✓', GREEN)] * 3 if ok else [('✓', GREEN), ('✗', RED), ('✓', GREEN)]
                title, acc = ('checks.json — все verified', GREEN) if ok else ('checks.json — ревью', RED)
            lines = []
            for (m, col), r in zip(marks, REQS):
                lines.append((m + '  ' + tr(r), col, 14))
                if col == RED:
                    lines.append(('     код: нет проверки category', MUTED, 13))
                else:
                    lines.append((tr('     код: add() · тест: test_') + ('amount' if 'amount' in r else 'id'), MUTED, 13))
            lines = lines[:6]
            card(c, LC, title, lines, 1, acc, active=s in (6, 8),
                 reveal=(lambda i: seg(p, 0.2 + i * 0.1, 0.3 + i * 0.1)) if s == 6 else None)
            if s == 7:
                c.tag(LC[0] + LC[2] - 10, LC[1] - 11, 'review --result rework', RED, seg(p, 0, 0.3), right=True)
            if s >= 8 and (s > 8 or p > 0.7):
                c.tag(LC[0] + LC[2] - 10, LC[1] - 11, 'review --result accepted', GREEN,
                      1 if s > 8 else seg(p, 0.7, 0.85), right=True)

    # packets on the MC → TM line
    if s == 1:
        c.packet([center(MC, 'b'), (MC[0] + 125, CARD_Y)], seg(p, 0, 0.3), 'пишет', YELLOW, seg(p, 0, 0.1) * (1 - seg(p, 0.35, 0.45)))
    if s == 2:
        c.packet([mc_r, tm_l], seg(p, 0.05, 0.6), 'ARCHITECTURE + functions.json', CYAN,
                 1 - seg(p, 0.7, 0.8))
    if s == 3:
        c.packet([mc_r, tm_l], seg(p, 0.05, 0.5), 'delegate', PURPLE, 1 - seg(p, 0.6, 0.7))

    # centre card: snapshot → inspect → tests → full run
    cc_lines, cc_title, cc_acc, cc_reveal = None, '', BORDER, None
    if s in (3, 4):
        cc_title, cc_acc = 'delegate · снимок до вызова', PURPLE
        cc_lines = [('требования заморожены', TEXT), ('хеши всех файлов проекта', TEXT),
                    ('scope: ExpenseService', TEXT), ('delegation_id: d-01', CYAN)]
        if s == 3:
            cc_reveal = lambda i: seg(p, 0.35 + i * 0.13, 0.5 + i * 0.13)
    elif s == 5:
        cc_title, cc_acc = 'inspect · что изменила попытка', PURPLE
        cc_lines = [('✓ app/expense_service.py — разрешён', GREEN), ('✓ tests/ не тронуты', GREEN),
                    ('✓ других изменений нет', GREEN), ('exit 0 → можно ревьюить', TEXT)]
        cc_reveal = lambda i: seg(p, 0.3 + i * 0.15, 0.45 + i * 0.15)
    elif s in (6, 7):
        cc_title, cc_acc = 'test --scope ExpenseService', RED
        cc_lines = [('test_add_returns_id              OK', GREEN, 13),
                    ('test_negative_amount_rejected    OK', GREEN, 13),
                    ('test_empty_category_rejected   FAIL', RED, 13),
                    ('exit 1 · 2 из 3', RED)]
        if s == 6:
            cc_reveal = lambda i: seg(p, 0.35 + i * 0.13, 0.5 + i * 0.13)
    elif s in (8, 9):
        cc_title, cc_acc = 'inspect ✓ · test --scope ExpenseService', GREEN
        cc_lines = [('test_add_returns_id              OK', GREEN, 13),
                    ('test_negative_amount_rejected    OK', GREEN, 13),
                    ('test_empty_category_rejected     OK', GREEN, 13),
                    ('exit 0 · 3 из 3', GREEN)]
        if s == 8:
            cc_reveal = lambda i: seg(p, 0.25 + i * 0.1, 0.35 + i * 0.1)
    elif s == 10:
        cc_title, cc_acc = 'test --scope full → finish', GREEN
        cc_lines = [('полный набор без фильтра', TEXT), ('exit 0 · все тесты OK', GREEN),
                    ('нет заданий без ревью', GREEN), ('finish → report.md', CYAN)]
        cc_reveal = lambda i: seg(p, 0.1 + i * 0.15, 0.25 + i * 0.15)
    if cc_lines:
        card(c, CC, cc_title, cc_lines, 1, cc_acc, active=s in (3, 5, 6, 8, 10), reveal=cc_reveal)
    if s == 5:
        c.packet([ex_l, tm_r], seg(p, 0.0, 0.3), 'вернул', ORANGE, 1 - seg(p, 0.35, 0.45))

    # right card: executor work → report
    if s in (4, 5, 6):
        top_lines = CODE1
        total = sum(len(t) + 1 for t, _ in top_lines)
        x, y, w, h = RC
        act = s == 4
        if act:
            c.glow(x, y, w, h, ORANGE)
        c.rr(x, y, w, h, PANEL, ORANGE if act else BORDER, 3 if act else 2, 12)
        c.t(x + 16, y + 12, 'app/expense_service.py', 15, 's', ORANGE, bg=PANEL)
        c.code(x + 16, y + 40, top_lines, total * seg(p, 0.2, 0.9) if act else None, 1, 13, 19)
        c.t(x + 16, y + h - 46, 'progress/d-01.json', 13, 'm', MUTED, bg=PANEL)
        cur = 'null' if (not act or p > 0.95) else '"add"'
        c.t(x + 16, y + h - 26, f'current_id: {cur}', 13, 'm', CYAN, bg=PANEL)
        if s == 4:
            c.packet(route_ex, seg(p, 0.0, 0.25), 'файл + спецификации', ORANGE, 1 - seg(p, 0.27, 0.33))
    elif s in (7, 8, 9):
        x, y, w, h = RC
        act = s in (7, 8)
        if act:
            c.glow(x, y, w, h, ORANGE)
        c.rr(x, y, w, h, PANEL, ORANGE if act else BORDER, 3 if act else 2, 12)
        c.t(x + 16, y + 12, 'попытка 2 · d-02', 15, 's', ORANGE, bg=PANEL)
        total = sum(len(t) + 1 for t, _ in CODE2)
        ch = total * seg(p, 0.35, 0.9) if s == 7 else None
        c.code(x + 16, y + 40, CODE2, ch, 1, 13, 19)
        if s == 7:
            c.packet(route_ex, seg(p, 0.0, 0.3), 'замечание + delegate', RED, 1 - seg(p, 0.32, 0.38))
    elif s == 10:
        rep = [('Время задачи', '18 мин'), ('Возвраты на доработку', '1'), ('Полные прогоны', '1 из 1'),
               ('Токены платных моделей', '120k'), ('Локальные · lmstudio', '340k'),
               ('Бесплатные облачные · :free', 'нет данных')]
        x, y, w, h = RC
        c.glow(x, y, w, h, GREEN, seg(p, 0.4, 0.6))
        c.rr(x, y, w, h, PANEL, GREEN, 2, 12)
        c.t(x + 16, y + 12, 'report.md — статистика (пример)', 15, 's', GREEN, bg=PANEL)
        for i, (k, v) in enumerate(rep):
            ai = seg(p, 0.35 + i * 0.08, 0.45 + i * 0.08)
            c.t(x + 16, y + 42 + i * 26, k, 14, 'r', MUTED, ai, bg=PANEL)
            c.t(x + w - 16, y + 42 + i * 26, v, 14, 's', TEXT, ai, anchor='ra', bg=PANEL)

    # loop-guard overlay
    if s == 9:
        a = seg(p, 0.0, 0.35)
        x, y, w, h = 150, 150, 900, 262
        c.rr(x, y, w, h, (32, 18, 20), RED, 3, 14, a)
        c.t(x + 24, y + 18, 'Защита от зацикливания → exit 3 STOP', 20, 'b', RED, a, bg=(32, 18, 20))
        guards = ['одно задание возвращено 3 раза (или 3 сбоя без изменений файлов)',
                  '3 прогона подряд без читаемого результата (сборка, таймаут, нет тестов)',
                  '12 красных рабочих прогонов подряд в одной области',
                  '60 прогонов с начала задачи или с последнего resume']
        for i, g in enumerate(guards):
            ai = a * seg(p, 0.2 + i * 0.12, 0.35 + i * 0.12)
            c.d.ellipse([x + 28, y + 66 + i * 34, x + 36, y + 74 + i * 34], fill=mix(RED, ai, (32, 18, 20)))
            c.t(x + 48, y + 59 + i * 34, g, 16, 'r', TEXT, ai, bg=(32, 18, 20))
        c.t(x + 24, y + h - 34, 'Дальше — только после решения пользователя: task_metrics resume --reason "…"',
            15, 's', YELLOW, a * seg(p, 0.7, 0.9), bg=(32, 18, 20))

    draw_dash(c, s, p)
    # pulse line from journal to dashboard
    if s in (2, 3, 4, 7, 8, 10):
        pts = [center(TM, 'b'), (TM[0] + 125, CARD_Y - 2)]
        c.dot(c.point_on([(TM[0] + 125, TM[1] + TM[3]), (TM[0] + 125, CARD_Y)], seg(p, 0.3, 0.6))[0],
              CYAN, 5, 1 - seg(p, 0.6, 0.7))


if __name__ == '__main__':
    n = build('../02_delegation_review_dashboard.gif', STEPS, draw, 'GIF 2/5',
              'Передача исполнителю, ревью и дашборд')
    print('frames', n)
