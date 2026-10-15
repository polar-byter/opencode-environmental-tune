"""Small drawing toolkit for the README explainer GIFs (Pillow only)."""
import os
import re
from PIL import Image, ImageDraw, ImageFont

LANG = os.environ.get('GIF_LANG', 'ru')
_CYR = re.compile('[А-Яа-яЁё]')
MISSES = set()
try:
    from i18n_en import EN as _EN
except ImportError:
    _EN = {}


def tr(s):
    """Translate a Russian UI string when rendering the English GIF set."""
    if LANG == 'ru' or not s:
        return s
    if s in _EN:
        return _EN[s]
    if _CYR.search(s):
        MISSES.add(s)
    return s

W, H = 1200, 675

BG = (13, 17, 23)
PANEL = (22, 27, 34)
PANEL2 = (30, 36, 44)
BORDER = (48, 54, 61)
TEXT = (230, 237, 243)
MUTED = (139, 148, 158)
DIM = (88, 96, 105)
BLUE = (56, 139, 253)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
ORANGE = (240, 136, 62)
YELLOW = (210, 168, 50)
PURPLE = (163, 113, 247)
CYAN = (57, 197, 207)
PINK = (219, 97, 162)

FONT_FILES = {
    'r': 'C:/Windows/Fonts/segoeui.ttf',
    's': 'C:/Windows/Fonts/seguisb.ttf',
    'b': 'C:/Windows/Fonts/segoeuib.ttf',
    'm': 'C:/Windows/Fonts/consola.ttf',
    'mb': 'C:/Windows/Fonts/consolab.ttf',
    'sym': 'C:/Windows/Fonts/seguisym.ttf',
}
SYMBOLS = set('✓✗⏸▶▸↻⟳✎')


def _runs(s):
    runs, cur, cur_sym = [], '', None
    for ch in s:
        sym = ch in SYMBOLS
        if cur and sym != cur_sym:
            runs.append((cur, cur_sym))
            cur = ''
        cur += ch
        cur_sym = sym
    if cur:
        runs.append((cur, cur_sym))
    return runs
_fonts = {}


def F(size, weight='r'):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_FILES[weight], size)
    return _fonts[key]


def ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def seg(p, a, b):
    """Progress of p inside the sub-range [a, b], clamped to 0..1."""
    if b <= a:
        return 1.0 if p >= b else 0.0
    return ease((p - a) / (b - a))


def mix(c, a, bg=BG):
    a = max(0.0, min(1.0, a))
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))


def appear(s, k, p):
    """Alpha of an element that appears at step k."""
    if s < k:
        return 0.0
    if s == k:
        return seg(p, 0.0, 0.45)
    return 1.0


class Cv:
    def __init__(self):
        self.im = Image.new('RGB', (W, H), BG)
        self.d = ImageDraw.Draw(self.im)

    # ---- primitives -------------------------------------------------
    def rr(self, x, y, w, h, fill=PANEL, outline=BORDER, width=2, r=12, a=1.0, bg=BG):
        if a <= 0:
            return
        self.d.rounded_rectangle(
            [x, y, x + w, y + h], r,
            fill=mix(fill, a, bg) if fill else None,
            outline=mix(outline, a, bg) if outline else None,
            width=width)

    def t(self, x, y, s, size=18, w='r', fill=TEXT, a=1.0, anchor='la', bg=BG):
        if a <= 0 or not s:
            return
        s = tr(s)
        col = mix(fill, a, bg)
        if not any(ch in SYMBOLS for ch in s):
            self.d.text((x, y), s, font=F(size, w), fill=col, anchor=anchor)
            return
        total = self.tlen(s, size, w)
        if anchor[0] == 'm':
            x -= total / 2
        elif anchor[0] == 'r':
            x -= total
        va = 'l' + anchor[1]
        for text, sym in _runs(s):
            font = F(size, 'sym') if sym else F(size, w)
            self.d.text((x, y), text, font=font, fill=col, anchor=va)
            x += self.d.textlength(text, font=font)

    def tlen(self, s, size=18, w='r'):
        return self._tlen(tr(s), size, w)

    def _tlen(self, s, size=18, w='r'):
        return sum(self.d.textlength(t, font=F(size, 'sym') if sym else F(size, w))
                   for t, sym in _runs(s))

    def wrap(self, s, size, w, maxw):
        s = tr(s)
        lines = []
        for para in s.split('\n'):
            cur = ''
            for word in para.split(' '):
                cand = (cur + ' ' + word).strip()
                if self._tlen(cand, size, w) <= maxw or not cur:
                    cur = cand
                else:
                    lines.append(cur)
                    cur = word
            lines.append(cur)
        return lines

    def para(self, x, y, s, maxw, size=16, w='r', fill=TEXT, a=1.0, lh=1.32, bg=BG):
        for line in self.wrap(s, size, w, maxw):
            self.t(x, y, line, size, w, fill, a, bg=bg)
            y += int(size * lh)
        return y

    def line(self, pts, color=MUTED, width=3, a=1.0, bg=BG):
        if a > 0:
            self.d.line(pts, fill=mix(color, a, bg), width=width, joint='curve')

    # ---- paths and arrows --------------------------------------------
    @staticmethod
    def _lengths(pts):
        out = []
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            out.append(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        return out

    def point_on(self, pts, t):
        lens = self._lengths(pts)
        total = sum(lens) or 1
        dist = total * max(0.0, min(1.0, t))
        for (p1, p2), ln in zip(zip(pts, pts[1:]), lens):
            if dist <= ln:
                k = dist / ln if ln else 0
                return (p1[0] + (p2[0] - p1[0]) * k, p1[1] + (p2[1] - p1[1]) * k), p1, p2
            dist -= ln
        return pts[-1], pts[-2], pts[-1]

    def arrow(self, pts, color=MUTED, a=1.0, width=3, prog=1.0, head=True, bg=BG):
        if a <= 0 or prog <= 0:
            return
        end, p1, p2 = self.point_on(pts, prog)
        drawn = []
        lens = self._lengths(pts)
        total = sum(lens) or 1
        dist = total * prog
        drawn.append(pts[0])
        for pt, ln in zip(pts[1:], lens):
            if dist >= ln:
                drawn.append(pt)
                dist -= ln
            else:
                break
        drawn.append(end)
        self.line(drawn, color, width, a, bg)
        if head and prog > 0.97:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            ln = (dx * dx + dy * dy) ** 0.5 or 1
            ux, uy = dx / ln, dy / ln
            s = 11
            tip = end
            left = (tip[0] - ux * s - uy * s * 0.6, tip[1] - uy * s + ux * s * 0.6)
            right = (tip[0] - ux * s + uy * s * 0.6, tip[1] - uy * s - ux * s * 0.6)
            self.d.polygon([tip, left, right], fill=mix(color, a, bg))

    def dot(self, xy, color=BLUE, r=7, a=1.0, bg=BG):
        if a <= 0:
            return
        x, y = xy
        self.d.ellipse([x - r - 5, y - r - 5, x + r + 5, y + r + 5], fill=mix(color, 0.25 * a, bg))
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=mix(color, a, bg))

    def packet(self, pts, t, label, color=BLUE, a=1.0):
        if a <= 0:
            return
        (x, y), _, _ = self.point_on(pts, t)
        size = 14
        w = self.tlen(label, size, 's') + 22
        self.rr(x - w / 2, y - 14, w, 28, fill=mix(color, 0.9), outline=color, width=2, r=14, a=a)
        self.t(x, y, label, size, 's', (255, 255, 255), a, anchor='mm', bg=mix(color, 0.9))

    # ---- composite shapes --------------------------------------------
    def glow(self, x, y, w, h, color, a=1.0, r=14):
        if a <= 0:
            return
        self.d.rounded_rectangle([x - 6, y - 6, x + w + 6, y + h + 6], r + 4,
                                 outline=mix(color, 0.30 * a), width=5)

    def node(self, x, y, w, h, title, sub='', color=BLUE, a=1.0, active=False,
             tsize=19, ssize=14, tag=None):
        if a <= 0:
            return
        if active:
            self.glow(x, y, w, h, color, a)
        self.rr(x, y, w, h, PANEL, color if active else BORDER, 3 if active else 2, 12, a)
        self.d.rounded_rectangle([x + 2, y + 10, x + 7, y + h - 10], 2, fill=mix(color, a))
        self.t(x + 20, y + 12, title, tsize, 's', TEXT, a, bg=PANEL)
        if sub:
            self.para(x + 20, y + 16 + tsize + 4, sub, w - 34, ssize, 'r', MUTED, a, bg=PANEL)
        if tag:
            self.tag(x + w - 12, y - 11, tag[0], tag[1], a, right=True)

    def tag(self, x, y, label, color=GREEN, a=1.0, right=False, size=13):
        if a <= 0:
            return
        w = self.tlen(label, size, 's') + 18
        if right:
            x = x - w
        self.rr(x, y, w, 22, fill=mix(color, 0.85), outline=None, r=11, a=a)
        self.t(x + w / 2, y + 11, label, size, 's', (255, 255, 255), a, anchor='mm', bg=mix(color, 0.85))
        return w

    def pageicon(self, x, y, color=MUTED, a=1.0, bg=PANEL, s=1.0):
        w, h, f = 20 * s, 26 * s, 7 * s
        pts = [(x, y), (x + w - f, y), (x + w, y + f), (x + w, y + h), (x, y + h)]
        self.d.polygon(pts, outline=mix(color, a, bg), fill=mix(color, 0.15 * a, bg))
        self.d.line([(x + w - f, y), (x + w - f, y + f), (x + w, y + f)], fill=mix(color, a, bg), width=1)
        for i in range(3):
            yy = y + 11 * s + i * 4.5 * s
            self.d.line([(x + 4 * s, yy), (x + w - 5 * s, yy)], fill=mix(color, 0.7 * a, bg), width=1)

    def doc(self, x, y, w, h, title, sub='', color=MUTED, a=1.0, active=False, tag=None):
        if a <= 0:
            return
        if active:
            self.glow(x, y, w, h, color, a)
        self.rr(x, y, w, h, PANEL, color if active else BORDER, 3 if active else 2, 10, a)
        self.pageicon(x + 14, y + 14, color if active else MUTED, a)
        self.t(x + 46, y + 10, title, 17, 's', TEXT, a, bg=PANEL)
        if sub:
            self.para(x + 46, y + 34, sub, w - 58, 13, 'r', MUTED, a, lh=1.25, bg=PANEL)
        if tag:
            self.tag(x + w - 10, y - 11, tag[0], tag[1], a, right=True)

    def window(self, x, y, w, h, title, a=1.0, active=False, color=BLUE):
        """A card with a title bar and three dots; returns body top y."""
        if a <= 0:
            return y + 34
        if active:
            self.glow(x, y, w, h, color, a)
        self.rr(x, y, w, h, PANEL, color if active else BORDER, 3 if active else 2, 10, a)
        self.d.rounded_rectangle([x + 2, y + 2, x + w - 2, y + 32], 9, fill=mix(PANEL2, a))
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = x + 18 + i * 16
            self.d.ellipse([cx - 5, y + 12, cx + 5, y + 22], fill=mix(c, 0.8 * a))
        self.t(x + 74, y + 17, title, 14, 'm', MUTED, a, anchor='lm', bg=PANEL2)
        return y + 42

    def code(self, x, y, lines, chars=None, a=1.0, size=14, lh=20, bg=PANEL):
        """lines: list of (text, color). chars limits how many characters are typed."""
        left = 10 ** 9 if chars is None else int(chars)
        for text, color in lines:
            if left <= 0:
                break
            shown = text[:left]
            left -= len(text) + 1
            self.t(x, y, shown, size, 'm', color, a, bg=bg)
            y += lh
        return y

    def cursor(self, xy, a=1.0, click=0.0):
        if a <= 0:
            return
        x, y = xy
        if click > 0:
            r = 10 + 16 * click
            self.d.ellipse([x - r, y - r, x + r, y + r], outline=mix(YELLOW, (1 - click) * a), width=3)
        pts = [(x, y), (x, y + 22), (x + 6, y + 17), (x + 10, y + 26), (x + 14, y + 24),
               (x + 10, y + 16), (x + 17, y + 16)]
        self.d.polygon(pts, fill=mix((255, 255, 255), a), outline=mix((0, 0, 0), a))

    def button(self, x, y, w, h, label, color=BLUE, a=1.0, filled=False, active=False, size=15, bg=PANEL):
        if a <= 0:
            return
        if active:
            self.d.rounded_rectangle([x - 4, y - 4, x + w + 4, y + h + 4], 10, outline=mix(color, 0.4 * a, bg), width=4)
        fill = color if filled else PANEL2
        self.rr(x, y, w, h, fill, color if (filled or active) else BORDER, 2, 8, a, bg=bg)
        self.t(x + w / 2, y + h / 2, label, size, 's',
               (255, 255, 255) if filled else TEXT, a, anchor='mm', bg=mix(fill, 1.0))

    def bar(self, x, y, w, h, frac, color=GREEN, a=1.0, bg=PANEL, frac2=None, color2=None):
        self.rr(x, y, w, h, PANEL2, None, 0, h // 2, a, bg=bg)
        if frac2:
            self.rr(x, y, max(h, w * frac2), h, color2, None, 0, h // 2, a, bg=bg)
        if frac > 0:
            self.rr(x, y, max(h, w * frac), h, color, None, 0, h // 2, a, bg=bg)


def chrome(c, num, title, s, steps, p):
    """Header, step dots and caption bar shared by every GIF."""
    c.t(30, 22, num, 15, 's', BLUE)
    c.t(30 + c.tlen(num, 15, 's') + 10, 15, title, 25, 'b', TEXT)
    n = len(steps)
    for i in range(n):
        cx = W - 30 - (n - 1 - i) * 18
        col = BLUE if i == s else (MUTED if i < s else BORDER)
        r = 5 if i == s else 4
        c.d.ellipse([cx - r, 30 - r, cx + r, 30 + r], fill=col)
    c.d.line([(30, 62), (W - 30, 62)], fill=BORDER, width=1)

    cap = tr(steps[s]['cap'])
    num, title = tr(num), tr(title)
    a = seg(p, 0.0, 0.35)
    y0 = H - 88
    c.rr(20, y0, W - 40, 72, (17, 23, 31), BORDER, 1, 12)
    lab = f'{s + 1}/{n}'
    c.rr(36, y0 + 22, 52, 28, BLUE, None, 0, 14)
    c.t(62, y0 + 36, lab, 15, 'b', (255, 255, 255), anchor='mm', bg=BLUE)
    lines = c.wrap(cap, 19, 'r', W - 160)
    yy = y0 + 36 - (len(lines) * 26) / 2 + 2
    for line in lines[:2]:
        c.t(104, yy, line, 19, 'r', TEXT, a, bg=(17, 23, 31))
        yy += 26
    total = sum(1 for _ in steps)
    frac = (s + p) / total
    c.d.rectangle([0, H - 4, int(W * frac), H], fill=BLUE)


def build(path, steps, draw, num, title, fps_ms=70):
    """Render all steps into an optimized looping GIF."""
    if LANG != 'ru':
        path = os.path.join(os.path.dirname(path), LANG, os.path.basename(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
    frames, durations = [], []
    for s, st in enumerate(steps):
        n = st.get('T', 8)
        for i in range(n + 1):
            p = i / n
            c = Cv()
            draw(c, s, p)
            chrome(c, num, title, s, steps, p)
            frames.append(c.im)
            durations.append(fps_ms if i < n else st.get('hold', 3200))
    # one shared palette keeps colors stable between frames
    k = 10
    picks = [frames[int(i * (len(frames) - 1) / (k - 1))] for i in range(k)]
    sample = Image.new('RGB', (W // 2, H // 2 * k))
    for i, fr in enumerate(picks):
        sample.paste(fr.resize((W // 2, H // 2)), (0, H // 2 * i))
    pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    out = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
    # merge identical consecutive frames
    merged, mdur = [out[0]], [durations[0]]
    for fr, du in zip(out[1:], durations[1:]):
        if fr.tobytes() == merged[-1].tobytes():
            mdur[-1] += du
        else:
            merged.append(fr)
            mdur.append(du)
    merged[0].save(path, save_all=True, append_images=merged[1:], duration=mdur,
                   loop=0, optimize=True, disposal=1)
    return len(merged)


def preview(draw, steps, num, title, out_dir, which=None):
    """Write the final frame of selected steps as PNG for visual review."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    for s in (which if which is not None else range(len(steps))):
        c = Cv()
        draw(c, s, 1.0)
        chrome(c, num, title, s, steps, 1.0)
        c.im.save(os.path.join(out_dir, f'step{s:02d}.png'))
