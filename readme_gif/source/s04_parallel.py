"""GIF 4: several executors in parallel, each in its own copy."""
from gifkit import *

STEPS = [
    dict(cap='Две части не зависят друг от друга: бюджет и распорядок дня. Общие договорённости '
             'Мастер Чиф зафиксировал заранее.', T=16, hold=4400),
    dict(cap='Контроллер делает каждому исполнителю отдельную копию файлов. Основной проект они не трогают.',
         T=22, hold=4400),
    dict(cap='Исполнители работают одновременно — каждый в своей копии, со своим учётом и своей сессией.',
         T=34, hold=4200),
    dict(cap='Сторож следит за каждой попыткой: шаги, время и повторы одних и тех же действий. При превышении лимита попытка останавливается.', T=18, hold=4600),
    dict(cap='Мастер Чиф проверяет каждую копию отдельно: что изменилось, тесты именно этой копии, все требования.',
         T=22, hold=4600),
    dict(cap='Принятые файлы переносятся в проект по одному. Если файл там успел измениться — '
             'перезаписи не будет.', T=26, hold=4600),
    dict(cap='После переноса — полный набор тестов уже на основном проекте.', T=16, hold=4800),
]

MAIN = (40, 230, 330, 300)
LANES = [('A', 'budget.py', 230), ('B', 'routine.py', 400)]
LX, LW, LH = 450, 710, 150


def main_project(c, s, p):
    x, y, w, h = MAIN
    green = s == 6 and p > 0.4
    c.rr(x, y, w, h, PANEL, GREEN if green else BORDER, 3 if green else 2, 16)
    c.t(x + 22, y + 18, 'Основной проект', 20, 's', TEXT, bg=PANEL)
    rows = [('contracts.py', 'договорённости', PURPLE, True)]
    for lab, name, _ in LANES:
        merged = s > 5 or (s == 5 and p > (0.45 if lab == 'A' else 0.85))
        rows.append(('app/' + name, '✓ перенесён' if merged else 'заготовка', GREEN if merged else MUTED, merged))
    for i, (f, st, col, ok) in enumerate(rows):
        yy = y + 62 + i * 62
        c.rr(x + 18, yy, w - 36, 50, PANEL2, None, 0, 10, bg=PANEL)
        c.t(x + 32, yy + 14, f, 16, 'm', TEXT, bg=PANEL2)
        c.t(x + 32, yy + 34, st, 13, 's' if ok else 'r', col, bg=PANEL2)
    if s == 6:
        c.t(x + 22, y + h - 34, 'все тесты: 42 из 42 ✓', 18, 's', GREEN, seg(p, 0.4, 0.7), bg=PANEL)


def lane(c, i, s, p):
    lab, name, y = LANES[i]
    a = appear(s, 1, p)
    if a <= 0:
        return
    act = s in (2, 3, 4)
    c.rr(LX, y, LW, LH, PANEL, ORANGE if act else BORDER, 3 if act else 2, 16, a)
    avatar(c, LX + 46, y + LH / 2, 26, lab, ORANGE, a)
    c.t(LX + 90, y + 26, tr('Копия {lab}').format(lab=lab) + ' · ' + name, 19, 's', TEXT, a, bg=PANEL)
    # progress
    if s >= 2:
        if s == 2:
            k = seg(p, 0.05 + i * 0.1, 0.9 - (0.15 if i else 0))
        else:
            k = 1.0
        c.t(LX + 90, y + 60, tr('функций готово'), 14, 'r', MUTED, a, bg=PANEL)
        c.bar(LX + 230, y + 64, 300, 12, k, ORANGE, a)
        c.t(LX + 545, y + 70, f'{int(round(k * 3))}/3', 14, 's', TEXT, a, anchor='lm', bg=PANEL)
    if s == 3:
        steps = [11, 8][i]
        c.t(LX + 90, y + 96, tr('шаги {a}/24 · время {b} из 10:00 · повторы 0/3').format(
            a=steps, b=['3:20', '2:05'][i]), 15, 'm', CYAN, seg(p, 0.2, 0.5), bg=PANEL)
    if s >= 4:
        a2 = seg(p, 0.15 + i * 0.25, 0.4 + i * 0.25) if s == 4 else 1
        c.t(LX + 90, y + 96, '✓ изменения проверены · ✓ тесты копии 5/5 · ✓ ревью', 15, 's', GREEN, a2,
            bg=PANEL)
    if s == 1:
        c.packet([(MAIN[0] + MAIN[2], MAIN[1] + 100 + i * 60), (LX, y + LH / 2)], seg(p, 0.1 + i * 0.25, 0.6 + i * 0.25),
                 tr('копия файлов'), PURPLE, 1 - seg(p, 0.85, 0.95))
    if s == 5:
        t0 = 0.05 if i == 0 else 0.45
        c.packet([(LX, y + LH / 2), (MAIN[0] + MAIN[2], MAIN[1] + 124 + i * 62)], seg(p, t0, t0 + 0.35),
                 tr('перенос'), GREEN, 1 - seg(p, t0 + 0.38, t0 + 0.42))


def draw(c, s, p):
    card(c, 40, 84, 330, 120, 'Мастер Чиф', 'две независимые части', BLUE, 1, active=s in (0, 4), badge='МЧ',
         tsize=21, ssize=15)
    main_project(c, s, p)
    if s >= 1:
        card(c, LX, 84, LW, 120, 'Контроллер', 'копии, сторож, перенос по одному', PURPLE, appear(s, 1, p),
             active=s in (1, 3, 5), badge='⚙', tsize=21, ssize=15)
    for i in range(2):
        lane(c, i, s, p)
    if s == 0:
        c.t(LX + 30, 300, 'budget.py и routine.py не зависят', 22, 's', MUTED, seg(p, 0.2, 0.5))
        c.t(LX + 30, 336, 'друг от друга — можно делать одновременно', 22, 's', MUTED, seg(p, 0.2, 0.5))


NUM, TITLE = 'GIF 4/8', 'Несколько исполнителей одновременно'

if __name__ == '__main__':
    print('frames', build('../04_parallel.gif', STEPS, draw, NUM, TITLE))
