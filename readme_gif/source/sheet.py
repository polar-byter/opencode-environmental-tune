"""Contact sheet of final frames for visual review: py sheet.py <module> <out.png>."""
import importlib, os, sys
import gifkit
from PIL import Image
m = importlib.import_module(sys.argv[1])
ims = []
for s in range(len(m.STEPS)):
    c = gifkit.Cv(); m.draw(c, s, 1.0); gifkit.chrome(c, m.NUM, m.TITLE, s, m.STEPS, 1.0)
    ims.append(c.im.resize((600, 338)))
rows = (len(ims) + 2) // 3
sh = Image.new('RGB', (1800, 338 * rows))
for i, im in enumerate(ims):
    sh.paste(im, ((i % 3) * 600, (i // 3) * 338))
sh.save(sys.argv[2])
