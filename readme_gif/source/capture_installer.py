"""Record real screenshots of the setup wizard (kit/installer_ui.py) for the README GIF.

    py readme_gif/source/capture_installer.py ru|en <out_dir>

Safe by design: the kit is installed into a temporary "my-home-app" folder inside
<out_dir> although the entry shows D:\\Projects\\my-home-app; opening Desktop and the
clipboard are disabled. "Prepare OpenCode" runs the real run_opencode --prepare-only
inside that temporary project (no model is called). The windows appear on screen
for about half a minute while frames are taken.
"""
import ctypes
import json
import shutil
import sys
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from kit import installer, installer_ui  # noqa: E402

LANG, OUT = sys.argv[1], Path(sys.argv[2])
SHOWN = r'D:\Projects\my-home-app'
TEMP_PROJECT = OUT / 'tmp' / 'my-home-app'


def frame_bounds(widget):
    """Window rectangle including the title bar, without the drop shadow."""
    hwnd = int(widget.wm_frame(), 16)
    rect = wintypes.RECT()
    try:
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
    except Exception:
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def main():
    if TEMP_PROJECT.parent.exists():
        shutil.rmtree(TEMP_PROJECT.parent)
    TEMP_PROJECT.parent.mkdir(parents=True)
    (OUT / 'frames').mkdir(parents=True, exist_ok=True)

    real_install = installer.install_project
    installer.install_project = lambda source, destination: real_install(source, str(TEMP_PROJECT))
    installer.open_project = lambda desktop, project: None

    window = installer_ui.tk.Tk()
    window.tk.call('tk', 'scaling', 96 / 72)  # render at the designed 100% size
    window.clipboard_clear = window.clipboard_append = lambda *a, **k: None
    ui = installer_ui.InstallerWindow(window, language=LANG)
    window.geometry('+40+30')
    window.attributes('-topmost', True)
    shots = []

    def shot(target, key, full_update=True):
        if target is None or not target.winfo_exists():
            return
        target.update_idletasks()
        if full_update:
            target.update()
        path = OUT / 'frames' / f'{len(shots):02d}_{key}.png'
        ImageGrab.grab(bbox=frame_bounds(target), all_screens=True).save(path)
        shots.append({'file': path.name, 'key': key})

    def config():
        return ui.config_window

    def hide_temp_path(widget):
        """Show the path the user typed instead of the temporary capture folder."""
        for child in widget.winfo_children():
            try:
                text = str(child.cget('text'))
            except Exception:
                text = ''
            if str(TEMP_PROJECT) in text:
                child.configure(text=text.replace(str(TEMP_PROJECT), SHOWN))
            hide_temp_path(child)

    steps = []

    def later(ms, fn):
        steps.append((ms, fn))

    ui.path.set('')
    later(700, lambda: shot(window, 'start'))
    for n in range(4, len(SHOWN) + 1, 5):
        later(150, lambda n=n: (ui.path.set(SHOWN[:n]), shot(window, 'typing')))
    later(150, lambda: (ui.path.set(SHOWN), shot(window, 'folder')))
    later(300, lambda: (ui.next_step(), shot(window, 'copying')))

    def wait_config():
        if not (config() and config().winfo_exists()):
            window.after(200, wait_config)
            return
        hide_temp_path(config())
        config().geometry('+60+20')
        config().attributes('-topmost', True)
        window.after(1500, after_config)

    def after_config():
        conf = ui.configuration
        shot(config(), 'chief')
        conf.notebook.select(conf.pages['exec'])
        window.after(700, lambda: (shot(config(), 'executors'), window.after(300, fixer)))

    def fixer():
        conf = ui.configuration
        conf.notebook.select(conf.pages['bug_fixer'])
        window.after(700, lambda: (shot(config(), 'fixer'), window.after(300, prepare)))

    def prepare():
        conf = ui.configuration
        conf.notebook.select(conf.pages['master_chief'])
        window.after(700, press_prepare)

    def press_prepare():
        conf = ui.configuration
        target = config()
        conf.on_prepare()
        shot(target, 'preparing', full_update=False)
        window.after(300, wait_prepared)

    def wait_prepared():
        if not ui.prepared:
            window.after(300, wait_prepared)
            return
        window.after(600, lambda: (shot(window, 'prepared'), window.after(300, copied)))

    def copied():
        ui.copy_prompt()
        window.after(400, lambda: (shot(window, 'prompt'), window.after(300, finish)))

    def finish():
        (OUT / 'shots.json').write_text(json.dumps(shots, indent=1), encoding='utf-8')
        window.destroy()

    def run(i=0):
        if i < len(steps):
            ms, fn = steps[i]
            window.after(ms, lambda: (fn(), run(i + 1)))
        else:
            window.after(200, wait_config)

    run()
    window.after(120000, window.destroy)  # safety net
    window.mainloop()
    installer.install_project = real_install
    shutil.rmtree(TEMP_PROJECT.parent, ignore_errors=True)
    print('shots', len(shots))


if __name__ == '__main__':
    main()
