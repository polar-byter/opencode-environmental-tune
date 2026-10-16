"""Render every step at several moments and list Russian strings without translation."""
import importlib
import os
import sys

os.environ['GIF_LANG'] = 'en'
import gifkit  # noqa: E402

MODS = ['s01_install', 's02_team', 's03_plan', 's04_parallel', 's05_bugfixer', 's06_final', 's07_models', 's08_dashboard']
for name in MODS:
    m = importlib.import_module(name)
    for s in range(len(m.STEPS)):
        for k in range(21):
            c = gifkit.Cv()
            m.draw(c, s, k / 20)
            gifkit.chrome(c, 'GIF', 'x', s, m.STEPS, k / 20)
out = sorted(gifkit.MISSES)
with open(sys.argv[1] if len(sys.argv) > 1 else 'misses.txt', 'w', encoding='utf-8') as f:
    for s in out:
        f.write(repr(s) + '\n')
print(len(out), 'missing')
