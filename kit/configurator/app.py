"""Window of the model configurator (we apply tkinter).

Run from the project root:
    py -m kit.configurator.app

The window has two sections, each with a radio button group to choose the source of the model:
- Master Chief (build, plan): "default from opencode.jsonc" / "model from OpenCode" / "own API";
- Executors: "LM Studio, already loaded model" / "own API".
Buttons: "Сохранить" writes .opencode/kit-models.json, "Применить" also runs
kit/run_opencode.py --prepare-only so the overlay is rebuilt, "Сбросить" deletes the
choice file.

Logic that does not need the window lives in module functions (form_to_choices,
choices_to_form, apply_choices) and is unit-tested. The ConfiguratorApp class only
draws widgets and calls those functions.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:  
    # Python built without Tkinter, or tests on other systems
    # replace it with a fake which does not need Tkinter.
    tk = ttk = None

from . import keys, models_choices_configurator, sources

# Values of the radio buttons; 
# they are also the keys of the form dictionary.
MASTER_CHIEF_DEFAULT, MASTER_CHIEF_OPENCODE, MASTER_CHIEF_API = 'default', 'opencode', 'api'
EXEC_LMSTUDIO, EXEC_API = 'lmstudio', 'api'

# Project root: kit/configurator/app.py ->we go 2 levels up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

#   Our form is a dictionary with these keys (these values are strings):
#   master_chief_source      MASTER_CHIEF_DEFAULT | MASTER_CHIEF_OPENCODE | MASTER_CHIEF_API
#   master_chief_model       model reference or model name
#   master_chief_url         API address (only for MASTER_CHIEF_API)
#   master_chief_key_env     name of the key variable (only for MASTER_CHIEF_API)
#   exec_source       EXEC_LMSTUDIO | EXEC_API
#   exec_instance     loaded instance ID or "" (only for EXEC_LMSTUDIO)
#   exec_model, exec_url, exec_key_env   (only for EXEC_API)
EMPTY_FORM = {
    'master_chief_source': MASTER_CHIEF_DEFAULT,
    'master_chief_model': '',
    'master_chief_url': '',
    'master_chief_key_env': keys.MASTER_CHIEF_KEY_ENV,
    'exec_source': EXEC_LMSTUDIO,
    'exec_instance': '',
    'exec_model': '',
    'exec_url': '',
    'exec_key_env': keys.EXECUTOR_KEY_ENV
}

# Step 7. Pure (independent from the window for our tests) Form -> choices (no window needed)
# so that we can unit-test the logic without the window. 
# The window only calls these functions.
def form_to_choices(form: dict) -> dict:   
    """Turn the values of the window fields into the content of the choice file.

    master_chief_source MASTER_CHIEF_DEFAULT -> no "masterChief" section;
    MASTER_CHIEF_OPENCODE -> models_choices_configurator.master_chief_from_opencode(master_chief_model);
    MASTER_CHIEF_API -> models_choices_configurator.api_choice(master_chief_url, master_chief_model, master_chief_key_env).
    exec_source EXEC_LMSTUDIO -> models_choices_configurator.lmstudio_choice(exec_instance);
    EXEC_API -> models_choices_configurator.api_choice(exec_url, exec_model, exec_key_env).
    Then models_choices_configurator.build_choices(master_chief, executors).

    Raises:
        ValueError: from the models_choices_configurator functions, or an unknown source value.
    """
    master_chief_source = form['master_chief_source']
    if master_chief_source == MASTER_CHIEF_DEFAULT:
        master_chief = None
    elif master_chief_source == MASTER_CHIEF_OPENCODE:
        master_chief = models_choices_configurator.master_chief_from_opencode(form['master_chief_model'])
    elif master_chief_source == MASTER_CHIEF_API:
        master_chief = models_choices_configurator.api_choice(form['master_chief_url'], form['master_chief_model'], form['master_chief_key_env'])
    else:
        raise ValueError(f'unknown master_chief_source: {master_chief_source}')
    exec_source = form['exec_source']
    if exec_source == EXEC_LMSTUDIO:
        executors = models_choices_configurator.lmstudio_choice(form['exec_instance'])
    elif exec_source == EXEC_API:
        executors = models_choices_configurator.api_choice(form['exec_url'], form['exec_model'], form['exec_key_env'])
    else:
        raise ValueError(f'unknown executor_source: {exec_source}')
    return models_choices_configurator.build_choices(master_chief, executors)


def choices_to_form(data: dict) -> dict:
    """The reverse: fill the form from a saved choice file, to show it when the window opens.

    Starts from a copy of EMPTY_FORM and overwrites the fields present in data.
    "masterChief" missing -> master_chief_source MASTER_CHIEF_DEFAULT; "executors" missing -> EXEC_LMSTUDIO.
    "instance" missing -> exec_instance "".
    """
    # ПОДСКАЗКА: копия словаря — dict(EMPTY_FORM) или EMPTY_FORM.copy().
    #   Без копии ты испортишь общий EMPTY_FORM (как общий static-объект в Java).
    # ПОДСКАЗКА: master_chief = data.get('masterChief'); if master_chief: ...; источник — master_chief['source'].
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


# Step 8. The window by itself, without the launcher (tkinter)
# what means "without the launcher": the window is a separate program, it does not run kit/run_opencode.py

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
        # ПОДСКАЗКА: затем self.build_master_chief_block(), self.build_executor_block(),
        #   self.build_buttons(), self.load_form().
        raise NotImplementedError('step 8.1: ConfiguratorApp.__init__')

    def build_master_chief_block(self):
        """Frame "Мастер Чиф (build, plan)": three radio buttons bound to vars['master_chief_source'],
        a combobox for master_chief_model, entries for master_chief_url and master_chief_key_env, a key entry
        hidden with "*", and a button "Обновить список" calling refresh_master_chief_models."""
        # ПОДСКАЗКА: ttk.LabelFrame(self.window, text='...') — рамка с заголовком.
        # ПОДСКАЗКА: ttk.Radiobutton(frame, text='...', variable=self.vars['master_chief_source'], value=MASTER_CHIEF_API)
        # ПОДСКАЗКА: ttk.Combobox(frame, textvariable=self.vars['master_chief_model'])
        # ПОДСКАЗКА: ttk.Entry(frame, textvariable=..., show='*') — поле пароля.
        # ПОДСКАЗКА: раскладка — .grid(row=..., column=..., sticky='w'), как GridBagLayout, только проще.
        raise NotImplementedError('step 8.2: build_master_chief_block')

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
        """Fill the variables from the saved choice file (models_choices_configurator.load_choices + choices_to_form).
        On a broken file show the error in the status label and keep EMPTY_FORM."""
        raise NotImplementedError('step 8.6: load_form')

    def refresh_master_chief_models(self):
        """Fill the Master Chief combobox: sources.opencode_models() for MASTER_CHIEF_OPENCODE,
        sources.api_models(url, key) for MASTER_CHIEF_API. Errors go to the status label."""
        raise NotImplementedError('step 8.7: refresh_master_chief_models')

    def refresh_lmstudio(self):
        """Fill the instance combobox from sources.lmstudio_instances()."""
        raise NotImplementedError('step 8.8: refresh_lmstudio')

    def on_save(self):
        """Save typed keys (keys.save_user_variable), then form_to_choices + models_choices_configurator.save_choices.
        Show "Сохранено: <path>" or the error text. Never show a key: use keys.mask."""
        raise NotImplementedError('step 8.9: on_save')

    def on_apply(self):
        """on_save, then apply_choices; show the exit code and the launcher output."""
        raise NotImplementedError('step 8.10: on_apply')

    def on_reset(self):
        """models_choices_configurator.reset_choices, then fill the form with EMPTY_FORM."""
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
