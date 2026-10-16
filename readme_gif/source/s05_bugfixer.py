"""GIF 5: when and how the bug fixer steps in."""
from gifkit import *

STEPS = [
    dict(cap='Исполнитель сдал работу, но проверка нашла ошибку: пустая категория не отклоняется.',
         T=18, hold=4200),
    dict(cap='Или сработал лимит: исполнитель исчерпал шаги или время. Контроллер подтверждает, что он остановлен.',
         T=18, hold=4400),
    dict(cap='Тогда работа один раз переходит исправителю ошибок: тот же файл, те же требования и текст ошибок.',
         T=22, hold=4400),
    dict(cap='Исправитель чинит только тела функций. Мастер Чиф проверяет заново — и принимает.',
         T=22, hold=4400),
    dict(cap='Ошибка API, лимит запросов (429), сломанная тестовая среда или пауза — исправителя не зовут.',
         T=18, hold=4600),
    dict(cap='Не справился и исправитель — работа останавливается (STOP) и ждёт решения человека. '
             'Обратно исполнителю она не уходит.', T=16, hold=5000),
]

EX = (40, 120, 330, 150)
RV = (435, 120, 330, 150)
BF = (830, 120, 330, 150)


def mid(box, side):
    x, y, w, h = box
    return {'l': (x, y + h / 2), 'r': (x + w, y + h / 2), 'b': (x + w / 2, y + h), 't': (x + w / 2, y)}[side]


def draw(c, s, p):
    card(c, *EX, 'Исполнитель', 'попытка 1', ORANGE, 1 if s < 4 else 0.5, active=s in (0, 1), badge='И', tsize=22)
    # review / limit box
    x, y, w, h = RV
    if s in (0, 1, 2):
        col = RED if s in (0, 2) else YELLOW
        c.rr(x, y, w, h, PANEL, col, 3, 16)
        if s == 0 or (s == 2):
            c.t(x + w / 2, y + 48, '✗ проверка не прошла', 21, 's', RED, anchor='mm', bg=PANEL)
            c.t(x + w / 2, y + 90, 'пустая категория → ошибка?', 16, 'r', MUTED, anchor='mm', bg=PANEL)
        else:
            c.t(x + w / 2, y + 48, '⏱ лимит попытки', 21, 's', YELLOW, anchor='mm', bg=PANEL)
            c.t(x + w / 2, y + 90, 'шаги 24 из 24 · остановлен ✓', 16, 'r', MUTED, anchor='mm', bg=PANEL)
        c.arrow([mid(EX, 'r'), mid(RV, 'l')], col, 1, 3, seg(p, 0, 0.4) if s in (0, 1) else 1)
    elif s == 3:
        c.rr(x, y, w, h, PANEL, GREEN, 3, 16)
        c.t(x + w / 2, y + 48, '✓ проверка прошла', 21, 's', GREEN, seg(p, 0.5, 0.7), anchor='mm', bg=PANEL)
        c.t(x + w / 2, y + 90, 'принято · перенесено в проект', 16, 'r', MUTED, seg(p, 0.6, 0.8), anchor='mm',
            bg=PANEL)
    a = appear(s, 2, p) if s < 4 else 0.5
    card(c, *BF, 'Исправитель ошибок', 'попытка 2 — единственная', PINK, a, active=s in (2, 3), badge='БФ',
         tsize=20, ssize=15)
    if s == 2:
        c.packet([mid(RV, 'r'), mid(BF, 'l')], seg(p, 0.2, 0.7), tr('код + требования + ошибки'), PINK,
                 1 - seg(p, 0.8, 0.9))
        items = ['тот же файл и те же требования', 'публичный текст ошибок тестов', 'свои лимиты шагов и времени']
        for i, t in enumerate(items):
            c.t(840, 310 + i * 36, '•  ' + tr(t), 17, 'r', TEXT, seg(p, 0.5 + i * 0.12, 0.65 + i * 0.12))
    if s == 3:
        c.packet([mid(BF, 'l'), mid(RV, 'r')], seg(p, 0.05, 0.45), tr('исправлено'), PINK, 1 - seg(p, 0.48, 0.55))
    if s == 4:
        c.t(40, 310, 'Исправителя не зовут, если:', 22, 's', TEXT, seg(p, 0, 0.2))
        items = [('ошибка API или 429', 'это не ошибка кода — ждём или меняем настройку'),
                 ('сломана тестовая среда', 'чинит Мастер Чиф или спрашивает тебя'),
                 ('пауза или отмена', 'решает пользователь')]
        for i, (t1, t2) in enumerate(items):
            a = seg(p, 0.15 + i * 0.2, 0.35 + i * 0.2)
            card(c, 40 + i * 380, 360, 360, 150, '✖ ' + tr(t1), t2, RED, a, tsize=19, ssize=15)
    if s == 5:
        a = seg(p, 0.1, 0.4)
        c.rr(300, 330, 600, 190, (32, 18, 20), RED, 3, 18, a)
        c.t(600, 385, '⛔ STOP', 40, 'b', RED, a, anchor='mm', bg=(32, 18, 20))
        c.t(600, 440, 'исправитель тоже не справился', 19, 's', TEXT, a, anchor='mm', bg=(32, 18, 20))
        c.t(600, 476, 'решает человек: уточнить задание, тесты или модель', 17, 'r', MUTED, a, anchor='mm',
            bg=(32, 18, 20))


NUM, TITLE = 'GIF 5/8', 'Исправитель ошибок: когда и как'

if __name__ == '__main__':
    print('frames', build('../05_bugfixer.gif', STEPS, draw, NUM, TITLE))
