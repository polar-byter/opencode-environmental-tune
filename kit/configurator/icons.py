"""Bundled original icons, loaded with Tk only; no runtime graphics dependency."""
from pathlib import Path

from . import app

ASSETS = Path(__file__).with_name('assets')


def navigation(window):
    scale = float(window.tk.call('tk', 'scaling')) / (96 / 72)
    size = 32 if scale <= 1.25 else 48 if scale <= 1.75 else 64
    return {name: {variant: app.tk.PhotoImage(master=window, file=str(ASSETS / f'{name}-{variant}-{size}.png'))
                   for variant in ('blue', 'white')}
            for name in ('master_chief', 'exec', 'catalog')}


def application(window):
    images = [app.tk.PhotoImage(master=window, file=str(ASSETS / f'app-{size}.png'))
              for size in (16, 32, 48, 64, 128, 256)]
    window.iconphoto(True, *images)
    return images
