"""GIF 6: the finish — UX/UI review by the Master Chief, full tests, report."""
from gifkit import *

STEPS = [
    dict(cap='Все части приняты и перенесены в проект. Остаётся то, что видит пользователь, — интерфейс.',
         T=16, hold=4000),
    dict(cap='Мастер Чиф запускает приложение и проходит обычные сценарии: добавить запись, изменить, удалить.',
         T=30, hold=4400),
    dict(cap='Отмечает, что мешает: бледный текст, кнопка без подписи, непонятное сообщение об ошибке.',
         T=22, hold=4600),
    dict(cap='Правки интерфейса — отдельный этап. Логика и договорённости не меняются, тесты снова проходят.',
         T=22, hold=4600),
    dict(cap='Финал: полный набор тестов, отчёт и файл запуска. Если интерфейс проверить не удалось, это отмечается в отчёте.', T=18, hold=5200),
]

AX, AY, AW, AH = 60, 90, 640, 480


def app(c, fixed, p, s):
    top = c.window(AX, AY, AW, AH, 'Домашний бюджет', 1, s in (1, 2, 3), BLUE)
    txt = TEXT if fixed else (120, 128, 138)
    c.t(AX + 26, top + 6, 'Покупки за неделю', 22, 'b', txt, bg=PANEL)
    rows = [('Молоко', '2 шт', '178 ₽'), ('Хлеб', '1 шт', '62 ₽'), ('Яблоки', '1,5 кг', '210 ₽')]
    for i, (a, b, cc) in enumerate(rows):
        y = top + 54 + i * 52
        c.rr(AX + 22, y, AW - 44, 44, PANEL2, None, 0, 8, bg=PANEL)
        c.t(AX + 40, y + 22, a, 17, 'r', txt, anchor='lm', bg=PANEL2)
        c.t(AX + 330, y + 22, b, 17, 'r', txt, anchor='lm', bg=PANEL2)
        c.t(AX + AW - 40, y + 22, cc, 17, 's', txt, anchor='rm', bg=PANEL2)
    by = top + 230
    if fixed:
        c.button(AX + 22, by, 220, 42, '+ Добавить покупку', GREEN, 1, filled=True, size=16)
    else:
        c.button(AX + 22, by, 60, 42, '+', GREEN, 1, filled=True, size=20)
    c.rr(AX + 22, by + 64, AW - 44, 52, PANEL2, RED if not fixed else GREEN, 2, 8, bg=PANEL)
    msg = 'Ошибка 422' if not fixed else 'Цена не может быть отрицательной'
    c.t(AX + 40, by + 90, msg, 16, 's', RED if not fixed else GREEN, anchor='lm', bg=PANEL2)
    return top, by


def draw(c, s, p):
    if s == 0:
        mods = ['budget.py', 'routine.py', 'storage.py', 'app.py']
        for i, m in enumerate(mods):
            a = seg(p, 0.05 + i * 0.15, 0.3 + i * 0.15)
            card(c, 160 + (i % 2) * 450, 150 + (i // 2) * 160, 420, 130, m, '✓ принят · ✓ перенесён', GREEN, a,
                 badge='✓', tsize=21, ssize=16)
        c.t(600, 520, 'код готов — но удобно ли им пользоваться?', 20, 's', MUTED, seg(p, 0.7, 0.95), anchor='mm')
        return
    fixed = s >= 3
    top, by = app(c, fixed, p, s)
    if s == 1:
        path = [(AX + 300, AY + 400), (AX + 50, by + 20), (AX + 400, top + 80), (AX + 400, top + 132)]
        k = seg(p, 0.05, 0.9)
        idx = min(len(path) - 2, int(k * (len(path) - 1)))
        loc = k * (len(path) - 1) - idx
        x = path[idx][0] + (path[idx + 1][0] - path[idx][0]) * loc
        y = path[idx][1] + (path[idx + 1][1] - path[idx][1]) * loc
        c.cursor((x, y), 1, click=(loc if loc > 0.8 else 0))
        steps = ['добавить покупку', 'изменить запись', 'ввести неверную цену']
        for i, t in enumerate(steps):
            c.t(740, 150 + i * 60, f'{i + 1}.  ' + tr(t), 20, 's', TEXT, seg(p, 0.1 + i * 0.25, 0.3 + i * 0.25))
    if s == 2:
        notes = [((AX + 200, top + 20), 'бледный текст — плохо читается'),
                 ((AX + 52, by + 21), 'кнопка «+» без подписи'),
                 ((AX + 130, by + 90), 'сообщение «Ошибка 422» непонятно')]
        for i, ((x, y), t) in enumerate(notes):
            a = seg(p, 0.1 + i * 0.25, 0.3 + i * 0.25)
            c.d.ellipse([x - 16, y - 16, x + 16, y + 16], outline=mix(YELLOW, a), width=3)
            c.rr(740, 140 + i * 110, 420, 90, PANEL, YELLOW, 2, 12, a)
            c.t(760, 162 + i * 110, f'{i + 1}', 22, 'b', YELLOW, a, bg=PANEL)
            c.para(796, 162 + i * 110, t, 350, 17, 'r', TEXT, a, bg=PANEL)
    if s == 3:
        card(c, 740, 140, 420, 120, 'Только интерфейс', 'подписи, контраст, понятные сообщения', BLUE,
             seg(p, 0.2, 0.45), badge='МЧ', tsize=20, ssize=15)
        card(c, 740, 280, 420, 120, 'Тесты снова зелёные', 'логика и договорённости те же', GREEN,
             seg(p, 0.5, 0.75), badge='✓', tsize=20, ssize=15)
    if s == 4:
        items = [('Полный набор тестов', '42 из 42 ✓ на основном проекте', GREEN, '✓'),
                 ('Отчёт', 'время, токены по ролям и попыткам, возвраты', CYAN, '▣'),
                 ('Файл запуска', 'run.ps1 — как запустить приложение', BLUE, '▶')]
        for i, (t1, t2, col, b) in enumerate(items):
            card(c, 740, 120 + i * 140, 420, 120, t1, t2, col, seg(p, 0.1 + i * 0.2, 0.35 + i * 0.2), badge=b,
                 tsize=20, ssize=15)


NUM, TITLE = 'GIF 6/8', 'Финал: интерфейс, тесты, отчёт'

if __name__ == '__main__':
    print('frames', build('../06_final.gif', STEPS, draw, NUM, TITLE))
