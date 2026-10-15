"""GIF 5: using the task dashboard and its controls."""
from gifkit import *

STEPS = [
    dict(cap='Дашборд открывается сам: task_metrics start запускает локальный сервер (127.0.0.1) '
             'и открывает страницу задачи. Команд вводить не нужно.', T=18, hold=3800),
    dict(cap='«Обзор»: статус, возвраты, прогоны тестов, сбои исполнителя и последние события. '
             'Страница обновляется каждые 2 секунды.', T=24, hold=4200),
    dict(cap='«Сейчас в работе»: модель, задание, текущая функция, принятые задания, токены '
             'и время. Устаревшая отметка функции скрывается через 90 секунд.', T=30, hold=4200),
    dict(cap='«Детализация работ»: каждое задание исполнителю — попытки, файлы, тесты, ревью '
             'и публичные действия моделей.', T=18, hold=4000),
    dict(cap='«Токены»: вход, выход, рассуждения и кэш по моделям и ролям. Неизвестное '
             'остаётся неизвестным и не заменяется нулём.', T=18, hold=4000),
    dict(cap='«Настройки моделей» открывает конфигуратор этого проекта. Ничего не сохраняется '
             'и не применяется автоматически — выбор действует для следующей задачи.', T=22, hold=4200),
    dict(cap='«Приостановить» прерывает основную сессию и всех её исполнителей. Пока идёт '
             'операция, виден переходный статус.', T=34, hold=4000),
    dict(cap='Пауза: код, план, история и очередь сообщений сохранены. Новые delegate, test, '
             'review и finish этой задачи заблокированы.', T=14, hold=4200),
    dict(cap='«Продолжить» отправляет в ту же основную сессию просьбу продолжить тот же task ID '
             'и проверить частичные правки. Защитные лимиты не сбрасываются.', T=30, hold=4600),
    dict(cap='«Остановить» прерывает всю семью сессий и очищает их очереди. Отмена — это не '
             'успешное завершение задачи.', T=30, hold=4200),
    dict(cap='«Удалить задачу…» — после подтверждения: остановка, затем удаление сессий и метрик '
             'этой задачи. Исходники приложения остаются.', T=34, hold=4600),
    dict(cap='После finish вместо «Сейчас в работе» — итог: время, полный прогон, ссылка '
             'на папку проекта, файл запуска и итоговый отчёт.', T=20, hold=5200),
]

WX, WY, WW, WH = 30, 72, 1140, 506
BTN_Y = 160
BTNS = [('⏸ Приостановить', 170), ('▶ Продолжить', 150), ('■ Остановить', 146), ('Удалить задачу…', 160)]


def btn_x(i):
    x = WX + 20
    for j in range(i):
        x += BTNS[j][1] + 10
    return x


def btn_center(i):
    return btn_x(i) + BTNS[i][1] / 2, BTN_Y + 17


def status_for(s, p):
    if s <= 5:
        return 'выполняется', BLUE
    if s == 6:
        return ('приостанавливается…', YELLOW) if p < 0.8 else ('пауза', YELLOW)
    if s == 7:
        return 'пауза', YELLOW
    if s == 8:
        return ('продолжается…', CYAN) if p < 0.7 else ('выполняется', BLUE)
    if s == 9:
        return ('останавливается…', ORANGE) if p < 0.75 else ('отменена', RED)
    if s == 10:
        if p < 0.6:
            return 'отменена', RED
        return ('удаление…', RED) if p < 0.85 else ('удалена', RED)
    return '✓ Работа завершена', GREEN


def tabs(c, active):
    x = WX + 20
    for i, lab in enumerate(['Обзор', 'Детализация работ', 'Токены']):
        w = c.tlen(lab, 15, 's') + 30
        act = i == active
        c.t(x + 15, 314, lab, 15, 's', TEXT if act else MUTED, anchor='lm', bg=PANEL)
        if act:
            c.d.rectangle([x, 330, x + w, 333], fill=BLUE)
        x += w + 6
    c.d.line([(WX + 20, 334), (WX + WW - 20, 334)], fill=BORDER)


def now_block(c, s, p, hl=False):
    x, y, w, h = WX + 20, 204, WW - 40, 86
    if s >= 11:
        a = seg(p, 0.1, 0.4)
        c.rr(x, y, w, h, mix(GREEN, 0.12, PANEL), GREEN, 2, 10, bg=PANEL)
        c.t(x + 16, y + 12, '✓ Работа завершена', 17, 'b', GREEN, a, bg=mix(GREEN, 0.12, PANEL))
        c.t(x + 16, y + 42, 'Время 41 мин · полный прогон: 128 тестов, OK', 14, 'r',
            TEXT, a, bg=mix(GREEN, 0.12, PANEL))
        bx = x + w - 16
        for lab, bw in [('Открыть итоговый отчёт', 196), ('Посмотреть файл запуска', 204),
                        ('Открыть папку проекта', 186)]:
            bx -= bw
            c.button(bx, y + 26, bw, 34, lab, GREEN, a, filled=lab.startswith('Открыть итог'), size=13,
                     bg=mix(GREEN, 0.12, PANEL))
            bx -= 10
        return
    paused = s in (7,) or (s == 6 and p > 0.8)
    col = YELLOW if paused else (RED if s >= 9 and (s > 9 or p > 0.75) else BLUE)
    if hl:
        c.glow(x, y, w, h, col)
    c.rr(x, y, w, h, PANEL2, col if hl else BORDER, 2, 10, bg=PANEL)
    title = tr('Сейчас в работе') + (tr(' · пауза') if paused else '')
    c.t(x + 16, y + 10, title, 15, 's', col, bg=PANEL2)
    k = seg(p, 0.1, 0.9) if s == 2 else 1.0
    func = ['add', 'total_for_week', 'remaining'][min(2, int(k * 2.99))] if s == 2 else 'total_for_week'
    impl = 4 + (int(k * 2) if s == 2 else 2)
    tok_in = 182 + (int(k * 24) if s == 2 else 24)
    items = [('Модель', 'исполнитель · qwen3.8-max'), ('Задание', 'ExpenseService'),
             ('Функция', func), ('Задания приняты', '1 / 3'), ('Функции реализованы', f'{impl} / 9'),
             ('Токены: вход / выход', f'{tok_in}k / 31k'), ('С начала задачи', '12:4' + str(1 + int(k * 3)))]
    cx = x + 16
    for i, (lab, val) in enumerate(items):
        iw = [190, 140, 140, 130, 150, 160, 120][i]
        c.t(cx, y + 38, lab, 12, 'r', MUTED, bg=PANEL2)
        c.t(cx, y + 56, val, 14, 's', TEXT, bg=PANEL2)
        cx += iw


def overview(c, s, p):
    tiles = [('Статус', status_for(s, p)[0]), ('Возвраты на доработку', '1'),
             ('Успешные прогоны / все', '3 / 5'), ('Сбои исполнителя', '0')]
    for i, (lab, val) in enumerate(tiles):
        tx = WX + 20 + i * 180
        c.rr(tx, 348, 168, 62, PANEL2, None, 0, 8, bg=PANEL)
        c.t(tx + 12, 356, lab, 12, 'r', MUTED, bg=PANEL2)
        c.t(tx + 12, 376, val, 17 if i else 15, 'b', TEXT, bg=PANEL2)
    c.t(WX + 20, 426, 'Посмотреть архитектуру кода →', 14, 's', BLUE, bg=PANEL)
    c.t(WX + 260, 426, 'Посмотреть детализацию работ →', 14, 's', BLUE, bg=PANEL)
    ex = WX + 760
    c.t(ex, 348, 'Последние события', 14, 's', MUTED, bg=PANEL)
    events = ['23:41  review ExpenseService · accepted', '23:39  test ExpenseService · OK 3/3',
              '23:38  inspect ExpenseService · clean', '23:36  delegate ExpenseService · d-02',
              '23:35  review ExpenseService · rework']
    shift = 1 - seg(p, 0.2, 0.6) if s == 1 else 0
    for i, ev in enumerate(events):
        a = 1.0
        if s == 1 and i == 0:
            a = seg(p, 0.3, 0.6)
        c.t(ex, 374 + i * 24 + shift * 0, ev, 13, 'm', TEXT if i == 0 else MUTED, a, bg=PANEL)


def details(c, s, p):
    cols = [(WX + 20, 'Задание'), (WX + 230, 'Попытки'), (WX + 330, 'Файл'), (WX + 640, 'Тесты'),
            (WX + 790, 'Ревью'), (WX + 930, 'Функции')]
    for x, lab in cols:
        c.t(x, 346, lab, 13, 's', MUTED, bg=PANEL)
    rows = [('ExpenseService', '2', 'app/expense_service.py', 'OK 3/3', 'принято', '3/3', GREEN),
            ('CategoryCatalog', '1', 'app/category_catalog.py', 'OK 4/4', 'принято', '2/2', GREEN),
            ('WeeklyReport', '1', 'app/weekly_report.py', '—', 'ждёт ревью', '1/4', YELLOW)]
    for i, r in enumerate(rows):
        a = seg(p, 0.1 + i * 0.2, 0.3 + i * 0.2)
        y = 374 + i * 36
        c.rr(WX + 14, y - 6, WW - 28, 32, PANEL2, None, 0, 6, a, bg=PANEL)
        for (x, _), val in zip(cols, r[:6]):
            col = r[6] if val in ('принято', 'ждёт ревью') else TEXT
            c.t(x, y + 2, val, 13, 'm' if '/' in val or '.' in val else 'r', col, a, bg=PANEL2)
    c.t(WX + 20, 490, 'Сообщения и действия моделей: публичные ответы и инструменты, без shell и рассуждений',
        13, 'r', MUTED, seg(p, 0.7, 0.9), bg=PANEL)


def tokens(c, s, p):
    cols = [(WX + 20, 'Модель / роль'), (WX + 420, 'Вход'), (WX + 540, 'Выход'), (WX + 660, 'Рассуждения'),
            (WX + 800, 'Кэш: чтение'), (WX + 940, 'Кэш: запись')]
    for x, lab in cols:
        c.t(x, 346, lab, 13, 's', MUTED, bg=PANEL)
    rows = [('openai/gpt-6.1-sol · Мастер Чиф', '412k', '58k', '21k', '1.2M', '—'),
            ('qwen3.8-max · исполнитель', '206k', '31k', 'неизвестно', '—', '—')]
    for i, r in enumerate(rows):
        a = seg(p, 0.15 + i * 0.25, 0.35 + i * 0.25)
        y = 374 + i * 36
        c.rr(WX + 14, y - 6, WW - 28, 32, PANEL2, None, 0, 6, a, bg=PANEL)
        for (x, _), val in zip(cols, r):
            c.t(x, y + 2, val, 13, 'r' if x == WX + 20 else 'm', MUTED if val in ('—', 'неизвестно') else TEXT,
                a, bg=PANEL2)
    c.t(WX + 20, 460, 'Категории не складываются в общий расход; денежная стоимость не вычисляется.', 13, 'r',
        MUTED, seg(p, 0.7, 0.9), bg=PANEL)


def session_tree(c, mode, p, a=1.0):
    """mode: 'pause', 'stop' or 'resume'."""
    x, y, w, h = 690, 300, 470, 262
    c.rr(x, y, w, h, (18, 22, 30), BORDER, 2, 12, a)
    c.t(x + 18, y + 14, 'Семья сессий задачи · общий сервер Desktop', 14, 's', MUTED, a, bg=(18, 22, 30))
    nodes = [('build · Мастер Чиф', x + 30, y + 50), ('executor · попытка d-07', x + 70, y + 110),
             ('executor-fast · правка', x + 70, y + 170)]
    for i, (lab, nx, ny) in enumerate(nodes):
        k = seg(p, 0.15 + i * 0.18, 0.3 + i * 0.18)
        if mode == 'pause':
            col, mark = (YELLOW, '⏸ прервана') if k > 0.5 else (BLUE, 'работает')
        elif mode == 'stop':
            col, mark = (RED, '■ очередь очищена') if k > 0.5 else (BLUE, 'работает')
        else:
            col, mark = (BLUE, 'продолжает') if (i == 0 and k > 0.5) else (YELLOW, '⏸')
        if i:
            c.line([(x + 46, ny - 24), (x + 46, ny + 18), (nx - 4, ny + 18)], BORDER, 2, a, (18, 22, 30))
        c.rr(nx, ny, 250, 36, PANEL2, col, 2, 8, a, bg=(18, 22, 30))
        c.t(nx + 12, ny + 18, lab, 13, 's', TEXT, a, anchor='lm', bg=PANEL2)
        c.t(x + w - 18, ny + 18, mark, 13, 's', col, a, anchor='rm', bg=(18, 22, 30))
    return y + h


def draw(c, s, p):
    wa = seg(p, 0.3, 0.8) if s == 0 else 1.0
    if s == 0:
        c.packet([(600, 72), (600, 300)], seg(p, 0.0, 0.35), 'task_metrics start', GREEN, 1 - seg(p, 0.35, 0.45))
    if wa <= 0:
        return
    top = c.window(WX, WY, WW, WH, 'http://127.0.0.1:8765/?task=expenses-20261015', wa)
    if wa < 1:
        c.d.rectangle([WX + 2, WY + 34, WX + WW - 2, WY + WH - 2], fill=mix(PANEL, wa))
        return
    c.t(WX + 20, 120, 'OpenCode · наблюдение за задачей', 18, 'b', TEXT, bg=PANEL)
    c.t(WX + 20 + c.tlen('OpenCode · наблюдение за задачей', 18, 'b') + 14, 124,
        'Автообновление каждые 2 секунды', 12, 'r', MUTED, bg=PANEL)
    # header controls on the right
    c.button(WX + WW - 190, 114, 170, 32, 'Настройки моделей', BLUE, 1, active=s == 5, size=14)
    c.button(WX + WW - 310, 114, 110, 32, 'В работе: 1', BLUE, 1, size=13)
    c.rr(WX + WW - 520, 114, 200, 32, PANEL2, BORDER, 2, 8, bg=PANEL)
    c.t(WX + WW - 508, 130, 'expenses-20261015  v', 13, 'm', TEXT, anchor='lm', bg=PANEL2)

    # task controls
    enabled = {
        'run': [True, False, True, True],
        'paused': [False, True, True, True],
        'cancelled': [False, False, False, True],
    }
    stat, scol = status_for(s, p)
    if stat in ('пауза', 'приостанавливается…'):
        en = enabled['paused']
    elif stat in ('отменена', 'останавливается…', 'удаление…', 'удалена'):
        en = enabled['cancelled']
    elif s >= 11:
        en = [False, False, False, True]
    else:
        en = enabled['run']
    hl = {6: 0, 8: 1, 9: 2, 10: 3}.get(s)
    for i, (lab, w) in enumerate(BTNS):
        col = [YELLOW, GREEN, ORANGE, RED][i]
        c.button(btn_x(i), BTN_Y, w, 34, lab, col, 1 if en[i] else 0.45, active=hl == i and p < 0.6, size=14)
    sw = c.tlen(stat, 14, 's') + 26
    c.rr(WX + WW - 20 - sw, BTN_Y + 4, sw, 28, mix(scol, 0.2, PANEL), scol, 2, 14, bg=PANEL)
    c.t(WX + WW - 20 - sw / 2, BTN_Y + 18, stat, 14, 's', scol, anchor='mm', bg=mix(scol, 0.2, PANEL))

    now_block(c, s, p, hl=s == 2)
    active_tab = {3: 1, 4: 2}.get(s, 0)
    tabs(c, active_tab)
    if s == 10 and p > 0.85:
        c.t(WX + 20, 360, 'Сессии и метрики задачи удалены. Исходники приложения на месте.', 16, 's', MUTED, bg=PANEL)
    elif active_tab == 0:
        overview(c, s, p)
    elif active_tab == 1:
        details(c, s, p)
    else:
        tokens(c, s, p)

    # cursor and overlays
    if s in (3, 4):
        tx = WX + 20 + (c.tlen('Обзор', 15, 's') + 36) + (0 if s == 3 else c.tlen('Детализация работ', 15, 's') + 36)
        c.cursor((tx + 40, 318), seg(p, 0, 0.15) * (1 - seg(p, 0.6, 0.7)), click=seg(p, 0.1, 0.3))
    if s == 5:
        c.cursor((WX + WW - 100, 132), seg(p, 0, 0.1) * (1 - seg(p, 0.5, 0.6)), click=seg(p, 0.1, 0.3))
        a = seg(p, 0.3, 0.5)
        top2 = c.window(660, 250, 500, 300, 'Модели проекта — OpenCode Kit', a, True)
        for i, (t1, t2) in enumerate([('Мастер Чиф', 'openai/gpt-6.1-sol'), ('Исполнители', 'qwen3.8-max · свой API'),
                                      ('OpenRouter', 'каталог и цены')]):
            c.rr(680, top2 + i * 62, 460, 52, PANEL2, BORDER, 2, 8, a, bg=PANEL)
            c.t(696, top2 + 8 + i * 62, t1, 15, 's', TEXT, a, bg=PANEL2)
            c.t(696, top2 + 28 + i * 62, t2, 13, 'm', MUTED, a, bg=PANEL2)
        c.t(680, top2 + 196, 'Сохранить и подготовить — отдельными кнопками', 13, 'r', YELLOW, a, bg=PANEL)
    if s in (6, 8, 9, 10):
        i = {6: 0, 8: 1, 9: 2, 10: 3}[s]
        bx, by = btn_center(i)
        c.cursor((bx + 200 * (1 - seg(p, 0, 0.15)), by + 60 * (1 - seg(p, 0, 0.15))),
                 1 - seg(p, 0.5, 0.6), click=seg(p, 0.15, 0.35))
    if s == 6:
        session_tree(c, 'pause', seg(p, 0.25, 1.0), seg(p, 0.2, 0.3))
    if s == 7:
        session_tree(c, 'pause', 1.0)
        c.tag(700, 290, 'delegate · test · review · finish — заблокированы', RED, seg(p, 0.1, 0.5))
    if s == 8:
        x, y, w, h = 690, 300, 470, 262
        a = seg(p, 0.2, 0.35)
        c.rr(x, y, w, h, (18, 22, 30), BORDER, 2, 12, a)
        c.t(x + 18, y + 14, 'Запрос в ту же основную сессию', 14, 's', MUTED, a, bg=(18, 22, 30))
        c.rr(x + 18, y + 44, w - 36, 104, PANEL2, CYAN, 2, 10, a, bg=(18, 22, 30))
        c.para(x + 32, y + 56, 'Продолжи задачу expenses-20261015: прочитай план и проверь частичные '
                               'изменения незавершённой попытки.', w - 64, 14, 'r', TEXT, a, bg=PANEL2)
        c.para(x + 18, y + 166, 'Генерация не продолжается «с того же токена» — Мастер Чиф продолжает '
                                'по плану. Защитные лимиты сохраняются.', w - 36, 14, 'r', MUTED,
               seg(p, 0.6, 0.8), bg=(18, 22, 30))
    if s == 9:
        session_tree(c, 'stop', seg(p, 0.25, 1.0), seg(p, 0.2, 0.3))
    if s == 10:
        a = seg(p, 0.3, 0.42) * (1 - seg(p, 0.75, 0.85))
        mx, my, mw, mh = 330, 230, 540, 220
        c.rr(mx, my, mw, mh, (26, 31, 39), RED, 3, 14, a)
        c.t(mx + 24, my + 20, 'Удалить задачу expenses-20261015?', 19, 'b', TEXT, a, bg=(26, 31, 39))
        c.para(mx + 24, my + 60, 'Сначала будет подтверждена остановка, затем удалятся сессии и метрики '
                                 'этой задачи. Исходники приложения останутся.', mw - 48, 15, 'r', MUTED, a,
               bg=(26, 31, 39))
        c.button(mx + mw - 300, my + mh - 56, 130, 36, 'Отмена', BLUE, a, size=14, bg=(26, 31, 39))
        c.button(mx + mw - 156, my + mh - 56, 132, 36, 'Удалить', RED, a, filled=True,
                 active=0.55 < p < 0.75, size=14, bg=(26, 31, 39))
        c.cursor((mx + mw - 90, my + mh - 38), a * seg(p, 0.45, 0.55), click=seg(p, 0.6, 0.72))


if __name__ == '__main__':
    n = build('../05_dashboard_controls.gif', STEPS, draw, 'GIF 5/5', 'Как управлять дашбордом')
    print('frames', n)
