"""Short GIF clips and covers for the Habr article drafts (habr_raw_docs/).

Each clip takes a few steps of an existing scene, shortens the pauses and
scales the frame to 960 px so the article loads fast.
"""
import importlib
import os

from PIL import Image

import gifkit
from gifkit import Cv, W, H, chrome, F, mix, BLUE, TEXT, MUTED, BG

OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'habr_raw_docs')
SCALE = 960 / W

CLIPS = {
    '01_osnovy_agentov': [
        ('planirovanie', 'gif1_planning', [1, 3, 4, 7, 9, 10], 'GIF 1', 'Как Мастер Чиф планирует'),
        ('dva_sposoba', 'gif3_setup', [7, 8], 'GIF 3', 'Два способа поставить задачу'),
        ('istochniki_modeley', 'gif3_setup', [2], 'GIF 3', 'Откуда берутся модели'),
        ('lmstudio_ili_openrouter', 'gif4_models', [0, 2, 7, 10], 'GIF 4', 'LM Studio и OpenRouter'),
    ],
    '02_podhod_i_uroki': [
        ('cikl_poruchenia', 'gif2_delegation', [1, 3, 4, 5], 'GIF 2', 'Поручение исполнителю'),
        ('revyu_i_vozvrat', 'gif2_delegation', [6, 7, 8], 'GIF 2', 'Ревью и возврат'),
        ('stop', 'gif2_delegation', [9], 'GIF 2', 'Защита от зацикливания'),
        ('itog', 'gif2_delegation', [10], 'GIF 2', 'Итог и отчёт'),
    ],
    '03_proverka_i_pult': [
        ('snimok_i_inspect', 'gif2_delegation', [3, 5], 'GIF 2', 'Снимок и inspect'),
        ('dashboard_vkladki', 'gif5_dashboard', [1, 2, 3, 4], 'GIF 5', 'Вкладки дашборда'),
        ('pauza_i_prodolzhenie', 'gif5_dashboard', [6, 7, 8], 'GIF 5', 'Пауза и продолжение'),
        ('ostanovka_i_udalenie', 'gif5_dashboard', [9, 10], 'GIF 5', 'Остановка и удаление'),
        ('vybor_modeli_lmstudio', 'gif4_models', [1, 2, 3], 'GIF 4', 'Как кит выбирает модель'),
    ],
}

COVERS = {
    '01_osnovy_agentov': ('gif1_planning', 11, 'ИИ-агенты без магии',
                          'прораб, бригада и журнал работ'),
    '02_podhod_i_uroki': ('gif2_delegation', 10, 'Дорогая модель проектирует, дешёвая пишет',
                          'что сломалось и что мы поправили'),
    '03_proverka_i_pult': ('gif5_dashboard', 7, 'Не верь агенту на слово',
                           'снимки файлов, STOP и пульт управления'),
}


def clip(folder, name, module, indices, num, title, hold=0.75):
    m = importlib.import_module(module)
    sub = [dict(m.STEPS[i]) for i in indices]
    for st in sub:
        st['hold'] = int(st.get('hold', 3200) * hold)
    frames, durations = [], []
    for k, (orig, st) in enumerate(zip(indices, sub)):
        n = st.get('T', 8)
        for i in range(n + 1):
            p = i / n
            c = Cv()
            m.draw(c, orig, p)
            chrome(c, num, title, k, sub, p)
            frames.append(c.im.resize((int(W * SCALE), int(H * SCALE)), Image.LANCZOS))
            durations.append(70 if i < n else st['hold'])
    path = os.path.join(OUT, folder, 'gifs', name + '.gif')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save(frames, durations, path)
    return path, sum(durations) / 1000


def save(frames, durations, path):
    k = min(10, len(frames))
    picks = [frames[int(i * (len(frames) - 1) / max(1, k - 1))] for i in range(k)]
    w, h = frames[0].size
    sample = Image.new('RGB', (w // 2, h // 2 * k))
    for i, fr in enumerate(picks):
        sample.paste(fr.resize((w // 2, h // 2)), (0, h // 2 * i))
    pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    out = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
    merged, mdur = [out[0]], [durations[0]]
    for fr, du in zip(out[1:], durations[1:]):
        if fr.tobytes() == merged[-1].tobytes():
            mdur[-1] += du
        else:
            merged.append(fr)
            mdur.append(du)
    merged[0].save(path, save_all=True, append_images=merged[1:], duration=mdur,
                   loop=0, optimize=True, disposal=1)


def cover(folder, module, step, title, subtitle):
    m = importlib.import_module(module)
    c = Cv()
    m.draw(c, step, 1.0)
    im = c.im.crop((0, 66, W, H - 96)).resize((W, H))
    # darken and put the title band on top
    shade = Image.new('RGB', im.size, BG)
    im = Image.blend(im, shade, 0.45)
    c2 = Cv()
    c2.im = im
    from PIL import ImageDraw
    c2.d = ImageDraw.Draw(c2.im)
    c2.rr(40, 220, W - 80, 220, (17, 23, 31), BLUE, 3, 18)
    c2.t(W / 2, 290, title, 46, 'b', TEXT, anchor='mm', bg=(17, 23, 31))
    c2.t(W / 2, 360, subtitle, 28, 'r', MUTED, anchor='mm', bg=(17, 23, 31))
    path = os.path.join(OUT, folder, 'cover.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c2.im.save(path)
    return path


if __name__ == '__main__':
    for folder, items in CLIPS.items():
        for name, module, indices, num, title in items:
            path, secs = clip(folder, name, module, indices, num, title)
            print(f'{path}  {secs:.0f}s  {os.path.getsize(path) // 1024} KB')
        print(cover(folder, *COVERS[folder]))
