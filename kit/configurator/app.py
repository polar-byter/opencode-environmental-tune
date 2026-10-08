"""Window of the model configurator (tkinter).

Run from the project root:

    py -m kit.configurator.app

The window has two blocks:
- Brain (build, plan): "default from opencode.jsonc" / "model from OpenCode" / "own API";
- Executors: "LM Studio, already loaded model" / "own API".
Buttons: "Сохранить" writes .opencode/kit-models.json, "Применить" also runs
kit/run_opencode.py --prepare-only so the overlay is rebuilt, "Сбросить" deletes the
choice file.

Logic that does not need the window lives in module functions (form_to_choices,
choices_to_form, apply_choices) and is unit-tested. The ConfiguratorApp class only
draws widgets and calls those functions.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Lines marked "ПОДСКАЗКА" are learning hints; delete them once the function is done.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:  # Python built without Tk: the pure functions below still work and are tested
    tk = ttk = None

from . import choices, keys, sources

# Values of the radio buttons. They are also the keys of the form dictionary.
BRAIN_DEFAULT, BRAIN_OPENCODE, BRAIN_API = 'default', 'opencode', 'api'
EXEC_LMSTUDIO, EXEC_API = 'lmstudio', 'api'

# Project root: kit/configurator/app.py -> three levels up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The form is a plain dictionary with these keys (all values are strings):
#   brain_source      BRAIN_DEFAULT | BRAIN_OPENCODE | BRAIN_API
#   brain_model       model reference or model name
#   brain_url         API address (only for BRAIN_API)
#   brain_key_env     name of the key variable (only for BRAIN_API)
#   exec_source       EXEC_LMSTUDIO | EXEC_API
#   exec_instance     loaded instance ID or "" (only for EXEC_LMSTUDIO)
#   exec_model, exec_url, exec_key_env   (only for EXEC_API)
EMPTY_FORM = {
    'brain_source': BRAIN_DEFAULT, 'brain_model': '', 'brain_url': '', 'brain_key_env': keys.BRAIN_KEY_ENV,
    'exec_source': EXEC_LMSTUDIO, 'exec_instance': '', 'exec_model': '', 'exec_url': '', 'exec_key_env': keys.EXECUTOR_KEY_ENV,
}


# --- Step 7. Form <-> choices (no window needed) ------------------------------

def form_to_choices(form: dict) -> dict:
    """Turn the values of the window fields into the content of the choice file.

    brain_source BRAIN_DEFAULT -> no "brain" section;
    BRAIN_OPENCODE -> choices.brain_from_opencode(brain_model);
    BRAIN_API -> choices.api_choice(brain_url, brain_model, brain_key_env).
    exec_source EXEC_LMSTUDIO -> choices.lmstudio_choice(exec_instance);
    EXEC_API -> choices.api_choice(exec_url, exec_model, exec_key_env).
    Then choices.build_choices(brain, executors).

    Raises:
        ValueError: from the choices functions, or an unknown source value.
    """
    # ПОДСКАЗКА: всю проверку уже делают функции из choices.py — здесь только if/elif/else.
    # ПОДСКАЗКА: form['brain_source'] бросит KeyError, если ключа нет; form.get(...) — нет.
    #   Здесь все ключи обязаны быть, так что можно квадратными скобками.
    raise NotImplementedError('step 7.1: form_to_choices')


def choices_to_form(data: dict) -> dict:
    """The reverse: fill the form from a saved choice file, to show it when the window opens.

    Starts from a copy of EMPTY_FORM and overwrites the fields present in data.
    "brain" missing -> brain_source BRAIN_DEFAULT; "executors" missing -> EXEC_LMSTUDIO.
    "instance" missing -> exec_instance "".
    """
    # ПОДСКАЗКА: копия словаря — dict(EMPTY_FORM) или EMPTY_FORM.copy().
    #   Без копии ты испортишь общий EMPTY_FORM (как общий static-объект в Java).
    # ПОДСКАЗКА: brain = data.get('brain'); if brain: ...; источник — brain['source'].
    raise NotImplementedError('step 7.2: choices_to_form')


def apply_choices(root: Path = PROJECT_ROOT) -> tuple[int, str]:
    """Rebuild the OpenCode overlay from the saved choice: run
    "<python> kit/run_opencode.py --prepare-only" in the project root.

    Returns:
        (exit code, combined stdout and stderr text) — the window shows the text.
    """
    # ПОДСКАЗКА: текущий интерпретатор Python — sys.executable (тот же, что запустил окно).
    # ПОДСКАЗКА: subprocess.run([...], cwd=root, capture_output=True, text=True, timeout=sources.TIMEOUT)
    # ПОДСКАЗКА: вернуть кортеж: return result.returncode, result.stdout + result.stderr
    raise NotImplementedError('step 7.3: apply_choices')


# --- Step 8. The window ---------------------------------------------------------

class ConfiguratorApp:
    """Main window. Holds one tkinter variable per form field.

    In Java Swing terms: the class builds JPanels with JRadioButtons, JComboBoxes and
    JTextFields; tkinter "variables" (StringVar) are like models bound to the widgets.
    """

    def __init__(self, window, root: Path = PROJECT_ROOT):
        """Remember the window and the project root, create the variables, build the
        widgets and fill them from the saved choice file (load_form)."""
        # ПОДСКАЗКА: self.window = window; self.root = root
        # ПОДСКАЗКА: по одной переменной на ключ формы:
        #   self.vars = {key: tk.StringVar(value=value) for key, value in EMPTY_FORM.items()}
        # ПОДСКАЗКА: затем self.build_brain_block(), self.build_executor_block(),
        #   self.build_buttons(), self.load_form().
        raise NotImplementedError('step 8.1: ConfiguratorApp.__init__')

    def build_brain_block(self):
        """Frame "Мозг (build, plan)": three radio buttons bound to vars['brain_source'],
        a combobox for brain_model, entries for brain_url and brain_key_env, a key entry
        hidden with "*", and a button "Обновить список" calling refresh_brain_models."""
        # ПОДСКАЗКА: ttk.LabelFrame(self.window, text='...') — рамка с заголовком.
        # ПОДСКАЗКА: ttk.Radiobutton(frame, text='...', variable=self.vars['brain_source'], value=BRAIN_API)
        # ПОДСКАЗКА: ttk.Combobox(frame, textvariable=self.vars['brain_model'])
        # ПОДСКАЗКА: ttk.Entry(frame, textvariable=..., show='*') — поле пароля.
        # ПОДСКАЗКА: раскладка — .grid(row=..., column=..., sticky='w'), как GridBagLayout, только проще.
        raise NotImplementedError('step 8.2: build_brain_block')

    def build_executor_block(self):
        """Frame "Исполнители (executor, executor-fast)": two radio buttons bound to
        vars['exec_source'], a combobox for exec_instance with "Обновить список"
        (refresh_lmstudio), entries for exec_url, exec_model, exec_key_env and the key."""
        raise NotImplementedError('step 8.3: build_executor_block')

    def build_buttons(self):
        """Bottom row: "Сохранить" (on_save), "Применить" (on_apply), "Сбросить" (on_reset)
        and a status label that shows the last result."""
        # ПОДСКАЗКА: ttk.Button(frame, text='Сохранить', command=self.on_save)
        #   command — это ссылка на метод, без скобок! Со скобками метод вызовется сразу.
        raise NotImplementedError('step 8.4: build_buttons')

    def read_form(self) -> dict:
        """Current values of all variables as a plain form dictionary."""
        # ПОДСКАЗКА: {key: var.get().strip() for key, var in self.vars.items()}
        raise NotImplementedError('step 8.5: read_form')

    def load_form(self):
        """Fill the variables from the saved choice file (choices.load_choices + choices_to_form).
        On a broken file show the error in the status label and keep EMPTY_FORM."""
        raise NotImplementedError('step 8.6: load_form')

    def refresh_brain_models(self):
        """Fill the brain combobox: sources.opencode_models() for BRAIN_OPENCODE,
        sources.api_models(url, key) for BRAIN_API. Errors go to the status label."""
        raise NotImplementedError('step 8.7: refresh_brain_models')

    def refresh_lmstudio(self):
        """Fill the instance combobox from sources.lmstudio_instances()."""
        raise NotImplementedError('step 8.8: refresh_lmstudio')

    def on_save(self):
        """Save typed keys (keys.save_user_variable), then form_to_choices + choices.save_choices.
        Show "Сохранено: <path>" or the error text. Never show a key: use keys.mask."""
        raise NotImplementedError('step 8.9: on_save')

    def on_apply(self):
        """on_save, then apply_choices; show the exit code and the launcher output."""
        raise NotImplementedError('step 8.10: on_apply')

    def on_reset(self):
        """choices.reset_choices, then fill the form with EMPTY_FORM."""
        raise NotImplementedError('step 8.11: on_reset')


def main() -> int:
    """Create the window and run the event loop until it is closed."""
    # ПОДСКАЗКА: tk и ttk уже импортированы в начале файла.
    #   window = tk.Tk(); window.title('Настройка моделей OpenCode')
    #   ConfiguratorApp(window); window.mainloop(); return 0
    # ПОДСКАЗКА: mainloop() — это цикл событий, как EDT в Swing: пока окно открыто, он не вернётся.
    raise NotImplementedError('step 8.12: main')


if __name__ == '__main__':
    sys.exit(main())
