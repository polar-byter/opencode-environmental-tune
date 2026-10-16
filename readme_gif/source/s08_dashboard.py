"""GIF 8: the dashboard — several workers, attempts, tokens and controls."""
from gifkit import *

STEPS = [
    dict(cap='Дашборд открывается сам, когда Мастер Чиф начинает задачу. Язык — как в браузере; '
             'переключатель «Язык» запоминает выбор.', T=18, hold=4400),
    dict(cap='«Сейчас в работе»: видно каждого участника — какой исполнитель над какой функцией работает.',
         T=26, hold=4600),
    dict(cap='«Детализация работ»: все попытки по каждому заданию — кто делал, чем закончилось, перенесено ли в проект.',
         T=20, hold=4800),
    dict(cap='«Токены»: расход по моделям и отдельно по каждой попытке. Если части данных нет, сумма помечается «≥».', T=20, hold=4800),
    dict(cap='«Приостановить» останавливает Мастер Чифа и всех исполнителей сразу. '
             '«Продолжить» — та же задача, с того же плана.', T=26, hold=4600),
    dict(cap='В конце — итог: ссылка на папку проекта, файл запуска и итоговый отчёт.', T=18, hold=5000),
]

WX, WY, WW, WH = 30, 76, 1140, 500


def header(c, s, p, status, scol):
    top = c.window(WX, WY, WW, WH, 'http://127.0.0.1:8765/?task=home-budget', 1)
    c.t(WX + 22, top + 2, 'OpenCode · наблюдение за задачей', 20, 'b', TEXT, bg=PANEL)
    c.rr(WX + WW - 190, top - 4, 170, 34, PANEL2, CYAN if s == 0 else BORDER, 2, 8, bg=PANEL)
    lang = 'Язык: Русский'
    c.t(WX + WW - 105, top + 13, lang, 14, 's', TEXT, anchor='mm', bg=PANEL2)
    c.button(WX + WW - 380, top - 4, 176, 34, 'Настройки моделей', BLUE, 1, size=14)
    bx = WX + 22
    labels = [('⏸ Приостановить', YELLOW), ('▶ Продолжить', GREEN), ('■ Остановить', ORANGE), ('Удалить задачу…', RED)]
    centers = []
    for lab, col in labels:
        w = c.tlen(lab, 14, 's') + 34
        paused = status in ('пауза', 'приостанавливается…')
        en = (lab.startswith('▶') and paused) or (not lab.startswith('▶') and not paused) or lab.startswith('■') \
            or lab.startswith('Удалить')
        c.button(bx, top + 44, w, 34, lab, col, 1 if en else 0.4, size=14)
        centers.append((bx + w / 2, top + 61))
        bx += w + 10
    sw = c.tlen(status, 15, 's') + 30
    c.rr(WX + WW - 22 - sw, top + 47, sw, 30, mix(scol, 0.22, PANEL), scol, 2, 15, bg=PANEL)
    c.t(WX + WW - 22 - sw / 2, top + 62, status, 15, 's', scol, anchor='mm', bg=mix(scol, 0.22, PANEL))
    return top + 96, centers


def tabs(c, y, active):
    x = WX + 22
    for i, lab in enumerate(['Обзор', 'Детализация работ', 'Токены']):
        w = c.tlen(lab, 16, 's') + 32
        c.t(x + 16, y + 14, lab, 16, 's', TEXT if i == active else MUTED, anchor='lm', bg=PANEL)
        if i == active:
            c.d.rectangle([x, y + 30, x + w, y + 33], fill=BLUE)
        x += w + 8
    c.d.line([(WX + 22, y + 34), (WX + WW - 22, y + 34)], fill=BORDER)
    return y + 50


def working(c, y, s, p, paused=False):
    c.rr(WX + 22, y, WW - 44, 150, PANEL2, YELLOW if paused else (BLUE if s == 1 else BORDER), 2, 12, bg=PANEL)
    title = tr('Сейчас в работе') + (tr(' · пауза') if paused else '')
    c.t(WX + 40, y + 12, title, 16, 's', YELLOW if paused else BLUE, bg=PANEL2)
    rows = [('A', 'Исполнитель A', 'budget · add_purchase', ORANGE, 0.66),
            ('B', 'Исполнитель B', 'routine · mark_done', ORANGE, 0.33)]
    for i, (b, who, what, col, frac) in enumerate(rows):
        yy = y + 46 + i * 48
        a = seg(p, 0.1 + i * 0.25, 0.35 + i * 0.25) if s == 1 else 1
        avatar(c, WX + 58, yy + 16, 15, b, col, a)
        c.t(WX + 84, yy + 16, who, 16, 's', TEXT, a, anchor='lm', bg=PANEL2)
        c.t(WX + 270, yy + 16, what, 16, 'm', TEXT, a, anchor='lm', bg=PANEL2)
        k = frac + (seg(p, 0.3, 0.95) * 0.3 if s == 1 else 0.3)
        c.bar(WX + 640, yy + 10, 300, 12, min(1, k), col, a, PANEL2)
        st = '⏸' if paused else tr('работает')
        c.t(WX + WW - 60, yy + 16, st, 15, 's', YELLOW if paused else GREEN, a, anchor='rm', bg=PANEL2)


def draw(c, s, p):
    status, scol = 'выполняется', BLUE
    if s == 4:
        status, scol = ('приостанавливается…', YELLOW) if p < 0.45 else (('пауза', YELLOW) if p < 0.75 else
                                                                         ('выполняется', BLUE))
    if s == 5:
        status, scol = '✓ Работа завершена', GREEN
    y, centers = header(c, s, p, status, scol)
    if s == 5:
        c.rr(WX + 22, y, WW - 44, 150, mix(GREEN, 0.12, PANEL), GREEN, 2, 12, bg=PANEL)
        c.t(WX + 42, y + 20, '✓ Работа завершена', 22, 'b', GREEN, bg=mix(GREEN, 0.12, PANEL))
        c.t(WX + 42, y + 58, 'Полный набор: 42 теста, OK · 4 задания приняты · 1 исправление', 16, 'r', TEXT,
            bg=mix(GREEN, 0.12, PANEL))
        bx = WX + 42
        for lab, fill in [('Открыть папку проекта', False), ('Посмотреть файл запуска', False),
                          ('Итоговый отчёт', True)]:
            w = c.tlen(lab, 15, 's') + 40
            c.button(bx, y + 92, w, 40, lab, GREEN, seg(p, 0.2, 0.5), filled=fill, size=15,
                     bg=mix(GREEN, 0.12, PANEL))
            bx += w + 14
    else:
        working(c, y, s, p, paused=(s == 4 and 0.45 <= p < 0.75))
    active = {2: 1, 3: 2}.get(s, 0)
    ty = tabs(c, y + 166, active)
    if active == 0:
        tiles = [('Статус', status), ('Возвраты на доработку', '1'), ('Успешные прогоны / все', '7 / 8'),
                 ('Сбои исполнителя', '0')]
        for i, (lab, val) in enumerate(tiles):
            x = WX + 22 + i * 276
            c.rr(x, ty, 264, 78, PANEL2, None, 0, 10, bg=PANEL)
            c.t(x + 16, ty + 14, lab, 14, 'r', MUTED, bg=PANEL2)
            c.t(x + 16, ty + 38, val, 21, 'b', TEXT, bg=PANEL2)
    elif active == 1:
        rows = [('budget', 'Попытка 1 · Исполнитель A', 'возврат: пустая категория', RED),
                ('budget', 'Попытка 2 · Bug Fixer', 'принято · изменения объединены', GREEN),
                ('routine', 'Попытка 1 · Исполнитель B', 'принято · изменения объединены', GREEN)]
        for i, (wi, att, res, col) in enumerate(rows):
            a = seg(p, 0.1 + i * 0.22, 0.3 + i * 0.22)
            yy = ty + i * 44
            c.rr(WX + 22, yy, WW - 44, 38, PANEL2, None, 0, 8, a, bg=PANEL)
            c.t(WX + 40, yy + 19, wi, 16, 'm', TEXT, a, anchor='lm', bg=PANEL2)
            c.t(WX + 190, yy + 19, att, 16, 's', TEXT, a, anchor='lm', bg=PANEL2)
            c.t(WX + WW - 40, yy + 19, res, 16, 's', col, a, anchor='rm', bg=PANEL2)
    else:
        rows = [('Master Chief · DeepSeek', '≥ 412 000', '58 000'),
                ('Исполнители · MiMo', '206 000', '31 000'),
                ('Bug Fixer · DeepSeek', '38 000', '6 000')]
        c.t(WX + 40, ty, 'Модель / роль', 14, 's', MUTED, bg=PANEL)
        c.t(WX + 620, ty, 'Вход', 14, 's', MUTED, bg=PANEL)
        c.t(WX + 800, ty, 'Выход', 14, 's', MUTED, bg=PANEL)
        for i, (m, a_in, a_out) in enumerate(rows):
            a = seg(p, 0.1 + i * 0.2, 0.3 + i * 0.2)
            yy = ty + 24 + i * 30
            c.t(WX + 40, yy, m, 16, 's', TEXT, a, bg=PANEL)
            c.t(WX + 620, yy, a_in, 16, 'm', YELLOW if '≥' in a_in else TEXT, a, bg=PANEL)
            c.t(WX + 800, yy, a_out, 16, 'm', TEXT, a, bg=PANEL)
        c.t(WX + 40, ty + 116, '≥ — у части сообщений нет данных; ноль не подставляется. Рядом — расход по каждой попытке.',
            14, 'r', YELLOW, seg(p, 0.7, 0.9), bg=PANEL)
    # cursor and pause flow
    if s in (2, 3):
        c.cursor((WX + 220 + (170 if s == 3 else 0), y + 182), seg(p, 0, 0.1) * (1 - seg(p, 0.5, 0.6)),
                 click=seg(p, 0.1, 0.3))
    if s == 4:
        k = 0 if p < 0.55 else 1
        cx, cy = centers[k]
        c.cursor((cx, cy), 1, click=seg(p, 0.1, 0.3) if k == 0 else seg(p, 0.6, 0.75))
        if 0.45 <= p < 0.75:
            c.t(WX + 22, WY + WH - 30, 'Основная модель и все связанные исполнители приостановлены.', 15, 's',
                YELLOW, bg=PANEL)
    if s == 0:
        c.cursor((WX + WW - 105, WY + 52), seg(p, 0.4, 0.5), click=seg(p, 0.55, 0.7))


NUM, TITLE = 'GIF 8/8', 'Дашборд: видно каждого исполнителя'

if __name__ == '__main__':
    print('frames', build('../08_dashboard.gif', STEPS, draw, NUM, TITLE))
