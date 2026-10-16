"""GIF 1: installing the kit with the setup wizard (install.cmd)."""
from gifkit import *

STEPS = [
    dict(cap='Нужны три вещи: OpenCode Desktop, Python 3.13 с Tk и архив кита с GitHub. '
             'Дальше — двойной щелчок по install.cmd.', T=20, hold=4200),
    dict(cap='Шаг 1. Мастер сам находит OpenCode Desktop. Если его нет — кнопка «Скачать OpenCode».',
         T=14, hold=3600),
    dict(cap='Шаг 2. Выбери папку для своего приложения. Если её нет, мастер создаст её сам.',
         T=20, hold=3600),
    dict(cap='Шаг 3. Мастер копирует кит в папку проекта и открывает окно настроек моделей.',
         T=22, hold=3800),
    dict(cap='Три роли уже заполнены бесплатными моделями. Нажми «Сохранить настройки», затем «Подготовить OpenCode».',
         T=24, hold=4400),
    dict(cap='Шаг 4. Проект открывается в Desktop. Скопируй пример задания, вставь в новый чат build и отправь.',
         T=24, hold=4800),
]

ROWS = [('1. OpenCode Desktop', '✓ Desktop найден'),
        ('2. Папка проекта', 'D:\\Projects\\my-home-app'),
        ('3. Установите кит и выберите модели', 'Создать проект и настроить модели'),
        ('4. Ваша первая задача', 'Копировать задание')]

WX, WY, WW, WH = 120, 84, 640, 492


def installer(c, active, p, s):
    top = c.window(WX, WY, WW, WH, 'Создание проекта — OpenCode Kit', 1)
    c.t(WX + 28, top + 4, 'Создайте проект OpenCode', 22, 'b', TEXT, bg=PANEL)
    for i, (title, value) in enumerate(ROWS):
        y = top + 50 + i * 100
        on = i == active
        done = i < active or (i == active and p > 0.85 and i < 3)
        col = BLUE if on else (GREEN if done else BORDER)
        c.rr(WX + 20, y, WW - 40, 86, mix(col, 0.12, PANEL) if on else PANEL2, col, 2, 12, bg=PANEL)
        c.t(WX + 40, y + 14, title, 17, 's', TEXT if (on or done) else MUTED, bg=PANEL2)
        a = 1.0 if i < active else (seg(p, 0.15, 0.6) if on else 0.0)
        if i == 0:
            c.t(WX + 40, y + 46, value, 16, 's', GREEN, a, bg=PANEL2)
        elif i == 1:
            n = int(len(value) * (seg(p, 0.1, 0.7) if on else 1))
            c.rr(WX + 40, y + 42, 420, 32, PANEL, BLUE if on else BORDER, 2, 6, 1 if i <= active else 0.3, bg=PANEL2)
            c.t(WX + 52, y + 58, value[:n] if i <= active else '', 15, 'm', TEXT, bg=PANEL)
        elif i == 2:
            c.button(WX + 40, y + 42, 330, 34, value, BLUE, 1 if i <= active else 0.35,
                     filled=i <= active, active=on and p < 0.5, size=15, bg=PANEL2)
            if i < active or (on and p > 0.6):
                c.t(WX + 390, y + 59, '✓ кит установлен', 15, 's', GREEN, 1 if i < active else seg(p, 0.6, 0.8),
                    anchor='lm', bg=PANEL2)
        else:
            c.button(WX + 40, y + 42, 220, 34, value, BLUE, 1 if on else 0.35, active=on and 0.3 < p < 0.6,
                     size=15, bg=PANEL2)


def scene(c, s, p):
    if s == 0:
        items = [('OpenCode Desktop', 'приложение, где работают агенты'),
                 ('Python 3.13 + Tk', 'для скриптов и окон кита'),
                 ('ZIP кита с GitHub', 'распаковать в отдельную папку')]
        for i, (t1, t2) in enumerate(items):
            a = seg(p, 0.05 + i * 0.18, 0.3 + i * 0.18)
            card(c, 50 + i * 375, 130, 350, 150, t1, t2, BLUE, a, badge='✓')
        a = seg(p, 0.7, 0.95)
        c.arrow([(600, 300), (600, 380)], BLUE, a, 4, a)
        c.rr(400, 390, 400, 120, mix(BLUE, 0.9), BLUE, 0, 18, a)
        c.t(600, 435, 'install.cmd', 30, 'b', (255, 255, 255), a, anchor='mm', bg=mix(BLUE, 0.9))
        c.t(600, 478, 'двойной щелчок — откроется мастер', 16, 'r', (225, 235, 255), a, anchor='mm',
            bg=mix(BLUE, 0.9))
        return
    if s in (1, 2, 3):
        installer(c, s - 1, p, s)
        if s == 3:
            files = ['AGENTS.md', 'opencode.jsonc', '.opencode/', 'kit/']
            c.t(800, 130, 'Скопировано в проект:', 17, 's', MUTED)
            for i, f in enumerate(files):
                a = seg(p, 0.25 + i * 0.12, 0.4 + i * 0.12)
                c.rr(800, 165 + i * 58, 340, 46, PANEL, GREEN, 2, 10, a)
                c.t(822, 188 + i * 58, '✓  ' + f, 17, 'm', TEXT, a, anchor='lm', bg=PANEL)
            if p > 0.85:
                c.t(800, 420, '→ открывается окно настроек', 17, 's', BLUE, seg(p, 0.85, 1))
        else:
            hint = {1: ('Нет Desktop?', 'кнопка «Скачать OpenCode», потом «Проверить ещё раз»'),
                    2: ('Своя папка', 'лучше отдельная, вне скачанного кита')}[s]
            card(c, 800, 200, 360, 150, hint[0], hint[1], ORANGE, seg(p, 0.4, 0.7))
        return
    if s == 4:
        top = c.window(80, 84, 700, 492, 'Модели проекта — OpenCode Kit', 1, True)
        roles = [('МЧ', 'Мастер Чиф', 'DeepSeek V4.1 Flash Free', BLUE),
                 ('И', 'Исполнители', 'MiMo V2.6 Flash Free · 1 одновременно', ORANGE),
                 ('БФ', 'Исправитель ошибок', 'DeepSeek V4.1 Flash Free', PINK)]
        for i, (b, t1, t2, col) in enumerate(roles):
            a = seg(p, 0.05 + i * 0.12, 0.25 + i * 0.12)
            card(c, 100, top + 8 + i * 104, 660, 92, t1, t2, col, a, badge=b, tsize=20)
        by = top + 330
        c.button(100, by, 210, 40, 'Сохранить настройки', BLUE, 1, filled=True, active=0.45 < p < 0.6, size=16)
        c.button(326, by, 260, 40, 'Подготовить OpenCode', BLUE, 1, active=0.62 < p < 0.85, size=16)
        cx = 205 if p < 0.6 else 205 + 251 * seg(p, 0.6, 0.65)
        c.cursor((cx, by + 22), seg(p, 0.4, 0.45) * (1 - seg(p, 0.9, 0.95)),
                 click=seg(p, 0.47, 0.57) if p < 0.6 else seg(p, 0.68, 0.8))
        c.t(100, by + 66, '✓ настройки подготовлены', 18, 's', GREEN, seg(p, 0.85, 0.95), bg=PANEL)
        card(c, 810, 140, 350, 150, 'Модель недоступна?', 'выбери другую в этом же окне', ORANGE, seg(p, 0.3, 0.5))
        card(c, 810, 310, 350, 150, 'Ключ API', 'хранится в Windows, не в проекте', YELLOW, seg(p, 0.4, 0.6))
        return
    # s == 5: first task in Desktop
    installer(c, 3, p, s)
    a = seg(p, 0.35, 0.5)
    top = c.window(790, 84, 380, 492, 'OpenCode Desktop · my-home-app', a, True, GREEN)
    c.rr(808, top + 4, 90, 28, mix(BLUE, 0.3, PANEL), BLUE, 1, 14, a, bg=PANEL)
    c.t(853, top + 18, 'build', 14, 's', TEXT, a, anchor='mm', bg=mix(BLUE, 0.3, PANEL))
    msg = ('Создай локальное приложение для домашних дел: список дел с датами и статусами, '
           'данные в SQLite. Следуй правилам кита и выполни весь план.')
    msg = tr(msg)
    n = int(len(msg) * seg(p, 0.5, 0.85))
    c.rr(808, top + 46, 344, 250, PANEL2, BORDER, 2, 12, a, bg=PANEL)
    c.para(824, top + 60, msg[:n], 312, 15, 'r', TEXT, a, bg=PANEL2)
    c.button(1032, top + 312, 120, 38, 'Отправить', GREEN, a, filled=True, active=p > 0.88, size=15)
    c.t(808, top + 370, 'задание отправляешь ты сам —', 14, 'r', MUTED, seg(p, 0.85, 1), bg=PANEL)
    c.t(808, top + 392, 'мастер ничего не шлёт модели', 14, 'r', MUTED, seg(p, 0.85, 1), bg=PANEL)


def draw(c, s, p):
    scene(c, s, p)


NUM, TITLE = 'GIF 1/8', 'Установка за четыре шага'

if __name__ == '__main__':
    print('frames', build('../01_install.gif', STEPS, draw, NUM, TITLE))
