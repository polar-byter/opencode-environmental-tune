"""Regenerate original vector icons and antialiased PNGs; Pillow is a build-only tool."""
from pathlib import Path

from PIL import Image, ImageDraw

FOLDER = Path(__file__).resolve().parent
BLUE = '#2563eb'
SHAPES = {
    'bug_fixer': [('line', ((4, 20), (12, 12), (11.5, 7), (15, 3.5), (15, 7.5),
                           (18, 10.5), (22, 10.5), (18.5, 14), (13.5, 13.5), (6, 21), (4, 20)))],
    'master_chief': [('rect', (8, 2.5, 16, 8), 1.5), ('line', ((12, 8), (12, 12))),
                     ('line', ((4.5, 15.5), (4.5, 12), (19.5, 12), (19.5, 15.5))),
                     ('line', ((12, 12), (12, 15.5))), ('rect', (1.5, 15.5, 7.5, 21.5), 1.3),
                     ('rect', (9, 15.5, 15, 21.5), 1.3), ('rect', (16.5, 15.5, 22.5, 21.5), 1.3)],
    'exec': [('line', ((7.5, 6.5), (2.5, 12), (7.5, 17.5))),
             ('line', ((16.5, 6.5), (21.5, 12), (16.5, 17.5))),
             ('line', ((14, 3.5), (10, 20.5)))],
    'catalog': [('rect', (2.5, 2.5, 9.5, 9.5), 1.7), ('rect', (14.5, 2.5, 21.5, 9.5), 1.7),
                ('rect', (2.5, 14.5, 9.5, 21.5), 1.7), ('rect', (14.5, 14.5, 21.5, 21.5), 1.7)],
}


def svg_shapes(shapes):
    parts = []
    for shape in shapes:
        if shape[0] == 'rect':
            x1, y1, x2, y2 = shape[1]
            parts.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" rx="{shape[2]}"/>')
        else:
            points = ' '.join(f'{x},{y}' for x, y in shape[1])
            parts.append(f'<polyline points="{points}"/>')
    return '\n  '.join(parts)


def render(shapes, size, color, badge=False):
    factor = size * 4 / 24
    image = Image.new('RGBA', (size * 4, size * 4))
    draw = ImageDraw.Draw(image)
    stroke = max(1, round(1.8 * factor))
    if badge:
        draw.rounded_rectangle((0, 0, size*4-1, size*4-1), radius=5.5*factor, fill='#142540')
        draw.rounded_rectangle((1*factor, 1*factor, 23*factor, 23*factor), radius=4.8*factor,
                               outline='#335b93', width=max(1, round(.65*factor)))
    for shape in shapes:
        if shape[0] == 'rect':
            box = tuple(value * factor for value in shape[1])
            draw.rounded_rectangle(box, radius=shape[2]*factor, outline=color, width=stroke)
        else:
            points = [(x*factor, y*factor) for x, y in shape[1]]
            draw.line(points, fill=color, width=stroke, joint='curve')
            for x, y in points:
                radius = stroke / 2
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main():
    for name, shapes in SHAPES.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
               f'stroke="{BLUE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">\n  '
               + svg_shapes(shapes) + '\n</svg>\n')
        (FOLDER / (name + '.svg')).write_text(svg, encoding='utf-8')
        for size in (32, 48, 64):
            for variant, color in (('blue', BLUE), ('white', '#ffffff')):
                icon = render(shapes, size, color)
                padded = Image.new('RGBA', (size + size // 4, size))
                padded.alpha_composite(icon)
                padded.save(FOLDER / f'{name}-{variant}-{size}.png')
    badge_shapes = [('rect', (7.5, 6, 16.5, 11.5), 1.5),
                    ('line', ((12, 11.5), (12, 15))), ('line', ((6.5, 17), (6.5, 15), (17.5, 15), (17.5, 17))),
                    ('rect', (4.5, 17, 8.5, 20), 1), ('rect', (10, 17, 14, 20), 1),
                    ('rect', (15.5, 17, 19.5, 20), 1)]
    (FOLDER / 'app.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n'
        '<rect width="24" height="24" rx="5.5" fill="#142540"/>\n'
        '<g fill="none" stroke="#9dccff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">\n  '
        + svg_shapes(badge_shapes) + '\n</g></svg>\n', encoding='utf-8')
    for size in (16, 32, 48, 64, 128, 256):
        render(badge_shapes, size, '#9dccff', badge=True).save(FOLDER / f'app-{size}.png')
    render(badge_shapes, 256, '#9dccff', badge=True).save(FOLDER / 'app.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])


if __name__ == '__main__':
    main()
