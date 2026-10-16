"""GIF 7: choosing models and limits in the configurator."""
from gifkit import *

STEPS = [
    dict(cap='Окно «Модели проекта»: у каждой роли своя модель. Открывается из мастера установки '
             'или кнопкой «Настройки моделей» в дашборде.', T=18, hold=4400),
    dict(cap='Источник модели: модель из OpenCode или свой API. Исполнителям доступна ещё и '
             'LM Studio на своём компьютере.', T=18, hold=4400),
    dict(cap='Исполнители: сколько работает одновременно и лимиты одной попытки. '
             '1 — по очереди, 2 и больше — параллельно.', T=22, hold=4800),
    dict(cap='Исправитель ошибок: своя модель и свои лимиты. Его можно выключить.', T=18, hold=4400),
    dict(cap='Каталог OpenRouter: отфильтруй модели для кода, щёлкни строку — модель подставится в выбранную роль.',
         T=24, hold=4600),
    dict(cap='Ключ хранится в Windows. «Проверить связь» → «Сохранить настройки» → «Подготовить OpenCode» → новый чат build.',
         T=26, hold=5000),
]

TABS = [('Мастер Чиф', BLUE), ('Исполнители', ORANGE), ('Исправитель ошибок', PINK), ('OpenRouter', PURPLE)]
WX, WY, WW, WH = 40, 84, 740, 492


def window(c, tab):
    top = c.window(WX, WY, WW, WH, 'Модели проекта — OpenCode Kit', 1)
    bw = (WW - 32 - 30) / 4
    for i, (lab, col) in enumerate(TABS):
        x = WX + 16 + i * (bw + 10)
        act = i == tab
        c.rr(x, top, bw, 48, mix(col, 0.25, PANEL) if act else PANEL2, col if act else BORDER, 2, 10, bg=PANEL)
        c.t(x + bw / 2, top + 24, lab, 15, 's', TEXT if act else MUTED, anchor='mm',
            bg=mix(col, 0.25, PANEL) if act else PANEL2)
    return top + 70


def field(c, x, y, w, label, value, active=False, a=1.0):
    c.t(x, y, label, 15, 's', MUTED, a, bg=PANEL)
    c.rr(x, y + 24, w, 38, PANEL2, BLUE if active else BORDER, 2, 8, a, bg=PANEL)
    c.t(x + 12, y + 43, value, 17, 'm', TEXT, a, anchor='lm', bg=PANEL2)


def side(c, items, p, start=0.2):
    for i, (t1, t2, col) in enumerate(items):
        card(c, 810, 100 + i * 158, 350, 140, t1, t2, col, seg(p, start + i * 0.18, start + 0.2 + i * 0.18),
             tsize=19, ssize=15)


def draw(c, s, p):
    if s == 0:
        y = window(c, 0)
        roles = [('МЧ', 'Мастер Чиф', 'архитектура, проверка, интерфейс', BLUE),
                 ('И', 'Исполнители', 'пишут код поручений', ORANGE),
                 ('БФ', 'Исправитель ошибок', 'одна попытка исправления', PINK)]
        for i, (b, t1, t2, col) in enumerate(roles):
            card(c, WX + 20, y + i * 112, WW - 40, 96, t1, t2, col, seg(p, 0.05 + i * 0.15, 0.3 + i * 0.15),
                 badge=b, tsize=20, ssize=15)
        side(c, [('Для каждой папки', 'выбор хранится в .opencode/kit-models.json', GREEN),
                 ('Без ключей в файлах', 'в файле только имя переменной Windows', YELLOW)], p, 0.5)
        return
    if s == 1:
        y = window(c, 1)
        opts = ['Локально · LM Studio', 'Модель из OpenCode', 'Свой API']
        k = int(seg(p, 0.1, 0.9) * 2.99)
        x = WX + 30
        for i, o in enumerate(opts):
            sel = i == k
            c.d.ellipse([x - 9, y + 12, x + 9, y + 30], outline=mix(BLUE if sel else MUTED, 1, PANEL), width=2)
            if sel:
                c.d.ellipse([x - 4, y + 17, x + 4, y + 25], fill=BLUE)
            c.t(x + 18, y + 21, o, 17, 's' if sel else 'r', TEXT if sel else MUTED, anchor='lm', bg=PANEL)
            x += c.tlen(o, 17, 's') + 60
        values = ['coder-32b-instruct', 'opencode/mimo-v2.6-flash-free', 'https://api.example.com/v1']
        labels = ['Загруженная модель', 'Модель OpenCode', 'Адрес API']
        field(c, WX + 24, y + 70, WW - 48, labels[k], values[k])
        side(c, [('Модель из OpenCode', 'модели, которые OpenCode уже знает, в т. ч. бесплатные', BLUE),
                 ('LM Studio', 'только для исполнителей: локально, модель загружаешь ты', GREEN),
                 ('Свой API', 'адрес …/v1, ключ и точное имя модели', PURPLE)], p, 0.15)
        return
    if s == 2:
        y = window(c, 1)
        field(c, WX + 24, y, WW - 48, 'Модель', 'opencode/mimo-v2.6-flash-free')
        vals = [('Одновременных исполнителей', '2'), ('Шагов на попытку', '24'),
                ('Секунд на попытку', '600'), ('Повторов без прогресса', '3')]
        for i, (lab, v) in enumerate(vals):
            x = WX + 24 + (i % 2) * 350
            yy = y + 90 + (i // 2) * 90
            cur = '1' if (i == 0 and p < 0.45) else v
            field(c, x, yy, 320, lab, cur, active=(i == 0 and 0.3 < p < 0.6), a=seg(p, 0.05 + i * 0.1, 0.2 + i * 0.1))
        side(c, [('1 — по очереди', 'надёжный режим по умолчанию', BLUE),
                 ('2 и больше — параллельно', 'только для частей, которые не зависят друг от друга', ORANGE),
                 ('Лимиты попытки', 'перебор шагов, времени или повторов — остановка', CYAN)], p, 0.4)
        return
    if s == 3:
        y = window(c, 2)
        field(c, WX + 24, y, WW - 48, 'Модель', 'opencode/deepseek-v4.1-flash-free')
        field(c, WX + 24, y + 90, 320, 'Шагов на попытку', '32', a=seg(p, 0.1, 0.3))
        field(c, WX + 374, y + 90, 320, 'Секунд на попытку', '600', a=seg(p, 0.2, 0.4))
        c.t(WX + 24, y + 196, 'или источник «Выключен» — исправителя не будет', 17, 'r', MUTED, seg(p, 0.5, 0.7),
            bg=PANEL)
        side(c, [('Когда работает', 'после ошибки кода или лимита исполнителя — одна попытка', PINK),
                 ('Когда нет', 'ошибки API и 429 его не запускают', RED)], p, 0.3)
        return
    if s == 4:
        y = window(c, 3)
        flt = ['✓ Для кода', '✓ Только с инструментами', 'Бесплатные']
        x = WX + 24
        for i, f in enumerate(flt):
            on = i < 2 or p > 0.35
            lab = ('✓ ' if (i == 2 and on) else '') + tr(f)
            w = c.tlen(lab, 15, 's') + 30
            c.rr(x, y, w, 34, mix(PURPLE, 0.3, PANEL) if on else PANEL2, PURPLE if on else BORDER, 2, 17, bg=PANEL)
            c.t(x + 15, y + 17, lab, 15, 's', TEXT if on else MUTED, anchor='lm',
                bg=mix(PURPLE, 0.3, PANEL) if on else PANEL2)
            x += w + 10
        c.t(WX + 24, y + 56, 'Подставить в:', 15, 'r', MUTED, bg=PANEL)
        c.rr(WX + 150, y + 48, 220, 34, mix(PINK, 0.3, PANEL), PINK, 2, 8, bg=PANEL)
        c.t(WX + 164, y + 65, 'Исправитель ошибок', 15, 's', TEXT, anchor='lm', bg=mix(PINK, 0.3, PANEL))
        rows = [('vendor-a/coder-pro', '1.20 / 4.80', False), ('vendor-b/dev-mini:free', '0 / 0', True),
                ('vendor-e/agent-coder:free', '0 / 0', True)]
        ry = y + 104
        for name, price, free in rows:
            if not free and p > 0.35:
                continue
            sel = name == 'vendor-e/agent-coder:free' and p > 0.6
            c.rr(WX + 20, ry - 4, WW - 40, 44, mix(BLUE, 0.35, PANEL) if sel else PANEL2, BLUE if sel else None, 1, 8,
                 bg=PANEL)
            bgc = mix(BLUE, 0.35, PANEL) if sel else PANEL2
            c.t(WX + 36, ry + 18, name, 16, 'm', TEXT, anchor='lm', bg=bgc)
            c.t(WX + WW - 36, ry + 18, price, 16, 'm', GREEN if free else TEXT, anchor='rm', bg=bgc)
            ry += 54
        c.cursor((WX + 300, y + 212 if p > 0.35 else y + 266), seg(p, 0.45, 0.5), click=seg(p, 0.55, 0.65))
        c.t(WX + 24, WY + WH - 40, 'условные данные · цены — $ за 1 млн токенов', 14, 'r', DIM, bg=PANEL)
        side(c, [('Каталог без ключа', 'грузится сам; цены — вход / выход', PURPLE),
                 ('Щелчок ничего не сохраняет', 'роль получает адрес OpenRouter и ID модели', BLUE)], p, 0.2)
        return
    # s == 5
    y = window(c, 1)
    field(c, WX + 24, y, WW - 48, 'Адрес API', 'https://openrouter.ai/api/v1')
    c.t(WX + 24, y + 90, '✓ Ключ найден', 17, 's', GREEN, bg=PANEL)
    c.t(WX + 170, y + 91, 'OPENROUTER_API_KEY — вводить снова не нужно', 15, 'm', MUTED, bg=PANEL)
    by = y + 140
    btns = [('Проверить связь', 180, False), ('Сохранить настройки', 210, True), ('Подготовить OpenCode', 220, False)]
    x = WX + 24
    centers = []
    for i, (lab, w, fill) in enumerate(btns):
        hl = int(seg(p, 0.1, 0.9) * 2.99) == i
        c.button(x, by, w, 42, lab, GREEN if i == 0 else BLUE, 1, filled=fill, active=hl, size=15)
        centers.append(x + w / 2)
        x += w + 14
    k = seg(p, 0.1, 0.9) * 2.99
    i = min(2, int(k))
    c.cursor((centers[i], by + 24), 1, click=(k - i) if (k - i) < 0.6 else 0)
    msgs = ['Связь установлена. OpenRouter принял ключ.', 'Настройки сохранены.', 'Настройки подготовлены.']
    for j in range(i + 1):
        c.t(WX + 24, by + 70 + j * 30, '✓ ' + tr(msgs[j]), 16, 's', GREEN, bg=PANEL)
    side(c, [('Текущий чат не переключится', 'открой новый чат build', ORANGE),
             ('Добавил новый ключ?', 'полностью перезапусти Desktop', YELLOW)], p, 0.6)


NUM, TITLE = 'GIF 7/8', 'Модели, лимиты и ключи'

if __name__ == '__main__':
    print('frames', build('../07_models.gif', STEPS, draw, NUM, TITLE))
