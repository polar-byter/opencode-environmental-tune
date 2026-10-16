"""GIF 2: who is in the team — roles at a glance."""
from gifkit import *

STEPS = [
    dict(cap='Ты описываешь задачу. Мастер Чиф — главный: строит план, договорённости между частями, '
             'тесты и проверяет результат.', T=18, hold=4400),
    dict(cap='Исполнители пишут код по готовым описаниям. Их может быть несколько — '
             'каждый работает в своей копии файлов.', T=16, hold=4200),
    dict(cap='Исправитель ошибок делает одну попытку, если исполнитель ошибся или упёрся в лимит.',
         T=16, hold=4200),
    dict(cap='Контроллер — обычная программа, не ИИ: раздаёт копии файлов, следит за лимитами '
             'и переносит принятый код в проект.', T=16, hold=4400),
    dict(cap='Каждый шаг записывается в журнал, а дашборд в браузере показывает, кто чем занят.',
         T=16, hold=4400),
    dict(cap='В конце Мастер Чиф проверяет интерфейс приложения и после этого завершает задачу.',
         T=14, hold=4800),
]

USER = (40, 250, 210, 120)
MC = (300, 220, 340, 180)
EX = (700, 84, 460, 112)
BF = (700, 216, 460, 112)
CT = (700, 348, 460, 112)
JR = (300, 450, 340, 112)


def mid(box, side):
    x, y, w, h = box
    return {'l': (x, y + h / 2), 'r': (x + w, y + h / 2), 't': (x + w / 2, y), 'b': (x + w / 2, y + h)}[side]


def draw(c, s, p):
    card(c, *USER, 'Ты', 'задача и решения', GREEN, 1, badge='Я', tsize=22)
    card(c, *MC, 'Мастер Чиф', 'план, договорённости, тесты, проверка', BLUE, 1,
         active=s in (0, 5), badge='МЧ', tsize=24)
    c.arrow([mid(USER, 'r'), mid(MC, 'l')], GREEN, 1, 3, seg(p, 0, 0.4) if s == 0 else 1)

    items = [(EX, 1, 'Исполнители', '1–8 одновременно, у каждого своя копия', ORANGE, 'И'),
             (BF, 2, 'Исправитель ошибок', 'одна попытка, если исполнитель не справился', PINK, 'БФ'),
             (CT, 3, 'Контроллер', 'программа: копии файлов, лимиты, перенос в проект', PURPLE, '⚙')]
    for box, k, t1, t2, col, b in items:
        a = appear(s, k, p)
        card(c, *box, t1, t2, col, a, active=s == k, badge=b, tsize=21, ssize=15)
        if a:
            x, y = mid(MC, 'r')
            tx, ty = mid(box, 'l')
            c.arrow([(x, y), (670, y), (670, ty), (tx - 2, ty)], col if s == k else BORDER, a, 3,
                    seg(p, 0.2, 0.6) if s == k else 1)
    if s >= 1:
        # several executors: small stacked badges
        a = appear(s, 1, p)
        for i, lab in enumerate(['A', 'B']):
            avatar(c, EX[0] + EX[2] - 46 - i * 40, EX[1] + 30, 15, lab, ORANGE, a)

    a = appear(s, 4, p)
    card(c, *JR, 'Журнал и дашборд', 'каждый шаг записан и виден', CYAN, a, active=s == 4, badge='▣',
         tsize=21, ssize=15)
    if a:
        c.arrow([mid(MC, 'b'), mid(JR, 't')], CYAN if s == 4 else BORDER, a, 3, seg(p, 0.2, 0.6) if s == 4 else 1)
        c.arrow([mid(CT, 'b'), (930, 520), (JR[0] + JR[2] + 2, 520)], CYAN if s == 4 else BORDER, a, 3,
                seg(p, 0.3, 0.7) if s == 4 else 1)

    if s == 5:
        c.tag(MC[0] + MC[2] - 12, MC[1] - 12, 'финальная проверка UX/UI', BLUE, seg(p, 0.1, 0.4), right=True, size=15)


NUM, TITLE = 'GIF 2/8', 'Кто в команде'

if __name__ == '__main__':
    print('frames', build('../02_team.gif', STEPS, draw, NUM, TITLE))
