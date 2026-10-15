# Configurator icons

Original vector artwork for the kit: architecture, code, bug-fixer wrench, catalog,
and application badge.
Navigation PNGs have blue and white variants at 32, 48 and 64 px, with transparent
spacing for the adjacent label. The application badge includes 16–256 px PNGs and an ICO.

The application uses Tk's PNG support; it does not require Pillow or an SVG renderer.
To regenerate the SVG/PNG/ICO assets during development with Pillow installed:

```text
python kit/configurator/assets/build_icons.py
```
