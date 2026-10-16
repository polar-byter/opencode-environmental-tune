"""Build 01_install_live.gif from real wizard screenshots (see capture_installer.py).

    py readme_gif/source/build_installer_gif.py ru|en <capture_dir>
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

LANG, CAP = sys.argv[1], Path(sys.argv[2])
os.environ['GIF_LANG'] = LANG
sys.path.insert(0, str(Path(__file__).parent))
import gifkit  # noqa: E402
from gifkit import W, H, BG, BORDER, Cv, chrome, tr  # noqa: E402

# Region of each window worth showing (pixels of the 100% capture).
CROPS = {
    'start': (0, 0, 844, 400), 'typing': (0, 0, 844, 400), 'folder': (0, 0, 844, 400),
    'copying': (0, 180, 844, 560),
    'chief': (0, 170, 944, 700), 'executors': (0, 170, 944, 700), 'fixer': (0, 170, 944, 700),
    'preparing': (0, 690, 944, 880),
    'prepared': (0, 380, 844, 830), 'prompt': (0, 380, 844, 830),
}
CAPTIONS = {
    'start': 'Двойной щелчок по install.cmd открывает мастер. Он уже нашёл OpenCode Desktop.',
    'typing': 'Шаг 2: путь к папке проекта. Недостающие папки мастер создаст сам.',
    'folder': 'Шаг 2: путь к папке проекта. Недостающие папки мастер создаст сам.',
    'copying': 'Шаг 3: «Создать проект и настроить модели» — кит копируется в папку проекта.',
    'chief': 'Открылось окно моделей. Мастер Чиф берёт модель из настроек проекта.',
    'executors': 'Исполнители: бесплатная MiMo V2.6 Flash, сколько работает одновременно и лимиты одной попытки.',
    'fixer': 'Исправитель ошибок: бесплатная DeepSeek V4.1 Flash и свои лимиты шагов и времени.',
    'preparing': '«Подготовить OpenCode» сохраняет выбор и собирает настройки. Модель при этом не вызывается.',
    'prepared': 'Готово: кнопка «Открыть проект в OpenCode». Мастер запускает Desktop с этой папкой.',
    'prompt': 'Шаг 4: «Копировать задание» — вставь его в новый чат build и отправь сам.',
}
HOLD = {'start': 3800, 'typing': 160, 'folder': 2600, 'copying': 3200, 'chief': 3400,
        'executors': 4200, 'fixer': 3600, 'preparing': 3400, 'prepared': 3600, 'prompt': 4600}
TITLE = 'Мастер установки'

TOP, BOTTOM = 72, H - 98


def framed(shot):
    """Crop the useful region, scale it into the content area and add a border."""
    img = Image.open(CAP / 'frames' / shot['file']).convert('RGB')
    box = CROPS[shot['key']]
    img = img.crop((box[0], box[1], min(box[2], img.width), min(box[3], img.height)))
    max_w, max_h = W - 60, BOTTOM - TOP - 10
    k = min(max_w / img.width, max_h / img.height)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    c = Cv()
    x, y = (W - img.width) // 2, TOP + (BOTTOM - TOP - img.height) // 2
    c.d.rounded_rectangle([x - 4, y - 4, x + img.width + 3, y + img.height + 3], 8, outline=BORDER, width=3)
    c.im.paste(img, (x, y))
    return c


def main():
    shots = json.loads((CAP / 'shots.json').read_text(encoding='utf-8'))
    # caption groups → steps for the progress dots
    steps, order = [], []
    for s in shots:
        cap = CAPTIONS[s['key']]
        if not steps or steps[-1]['cap'] != cap:
            steps.append({'cap': cap})
        order.append(len(steps) - 1)
    frames, durations = [], []
    prev = None
    for s, idx in zip(shots, order):
        base = framed(s)
        chrome(base, 'GIF', TITLE, idx, steps, 1.0)
        cur = base.im
        if prev is not None and s['key'] != 'typing':
            for t in (0.25, 0.5, 0.75):  # short cross-fade between screens
                frames.append(Image.blend(prev, cur, t))
                durations.append(60)
        frames.append(cur)
        durations.append(HOLD[s['key']])
        prev = cur
    out = Path(__file__).resolve().parents[1] / ('en' if LANG == 'en' else '') / '01_install_live.gif'
    out.parent.mkdir(exist_ok=True)
    k = min(10, len(frames))
    picks = [frames[int(i * (len(frames) - 1) / (k - 1))] for i in range(k)]
    sample = Image.new('RGB', (W // 2, H // 2 * k))
    for i, fr in enumerate(picks):
        sample.paste(fr.resize((W // 2, H // 2)), (0, H // 2 * i))
    pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
    q[0].save(out, save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=True, disposal=1)
    print(out, len(q), 'frames', round(sum(durations) / 1000), 's', out.stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    main()
