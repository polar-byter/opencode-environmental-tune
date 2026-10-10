"""Window of the model configurator (we apply tkinter).

Run from the project root:
    py -m kit.configurator.app

The window has two sections, each with a radio button group to choose the source of the model:
- Master Chief (build, plan): "default from opencode.jsonc" / "model from OpenCode" / "own API";
- Executors: "LM Studio, already loaded model" / "own API".
Buttons: "Save" writes .opencode/kit-models.json, "Apply" also runs
kit/run_opencode.py --prepare-only so the overlay is rebuilt, "Reset" deletes the
choice file.

Logic that does not need the window lives in module functions (form_to_choices,
choices_to_form, apply_choices) and is unit-tested. The ConfiguratorApp class only
draws widgets and calls those functions.
"""
from __future__ import annotations

import os
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
    #result_form = {k: v for k, v in EMPTY_FORM.items()}
    result_form = dict(EMPTY_FORM)  # copy
    master_chief = data.get('masterChief')    
    if master_chief is not None:
        if master_chief['source'] == MASTER_CHIEF_OPENCODE:
            result_form['master_chief_source'] = MASTER_CHIEF_OPENCODE
            result_form['master_chief_model'] = master_chief['model']
        elif master_chief['source'] == MASTER_CHIEF_API:
            result_form['master_chief_source'] = MASTER_CHIEF_API
            result_form['master_chief_model'] = master_chief['model']
            result_form['master_chief_url'] = master_chief['baseURL']
            result_form['master_chief_key_env'] = master_chief['keyEnv']
    executors = data.get('executors')
    if executors is not None:
        if executors['source'] == EXEC_LMSTUDIO:
            result_form['exec_source'] = EXEC_LMSTUDIO
            result_form['exec_instance'] = executors.get('instance', '')
        elif executors['source'] == EXEC_API:
            result_form['exec_source'] = EXEC_API
            result_form['exec_model'] = executors['model']
            result_form['exec_url'] = executors['baseURL']
            result_form['exec_key_env'] = executors['keyEnv']
       
    return result_form
    


def apply_choices(root: Path = PROJECT_ROOT) -> tuple[int, str]:
    """Rebuild the OpenCode overlay from the saved choice: run
    "<python> kit/run_opencode.py --prepare-only" in the project root.

    Returns:
        (exit code, combined stdout and stderr text) — the window shows the text.
    """
    root = Path(root)
    subprocess_args = [sys.executable, str( Path('kit') / "run_opencode.py"), '--prepare-only']
    subprocess_kwargs = {
        'cwd': root,
        'capture_output': True,
        'text': True,
        'timeout': sources.TIMEOUT
    }
    subprocess_result = subprocess.run(subprocess_args, **subprocess_kwargs)
    return subprocess_result.returncode, subprocess_result.stdout + subprocess_result.stderr


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
        self.window = window
        self.root = root
        self.vars = {key: tk.StringVar(value=value) for key, value in EMPTY_FORM.items()}
        self.build_master_chief_block()
        self.window.columnconfigure(0, weight=1)
        self.build_executor_block()
        self.build_buttons()
        self.load_form()


    def build_master_chief_block(self):
        """Frame "Master Chief (build, plan)": three radio buttons bound to vars['master_chief_source'],
        a combobox for master_chief_model, entries for master_chief_url and master_chief_key_env, a key entry
        hidden with "*", and a button "Refresh list" calling refresh_master_chief_models."""
        # 1. The frame with a title. Created and placed in two separate lines:
        #    .grid() returns None, so "frame = ttk.LabelFrame(...).grid(...)" would store None.
        frame = ttk.LabelFrame(self.window, text='Master Chief (build, plan)')
        frame.grid(row=0, column=0, sticky='ew', padx=8, pady=4)
        frame.columnconfigure(1, weight=1)  # column 1 (the fields) stretches with the window

        # 2. Three radio buttons in row 0. One shared variable makes them a group:
        #    choosing one clears the others. Each button writes its own value into the variable.
        source = self.vars['master_chief_source']
        ttk.Radiobutton(frame, text='Default (opencode.jsonc)', variable=source,
                        value=MASTER_CHIEF_DEFAULT).grid(row=0, column=0, sticky='w', padx=4, pady=2)
        ttk.Radiobutton(frame, text='Model from OpenCode', variable=source,
                        value=MASTER_CHIEF_OPENCODE).grid(row=0, column=1, sticky='w', padx=4, pady=2)
        ttk.Radiobutton(frame, text='Own API', variable=source,
                        value=MASTER_CHIEF_API).grid(row=0, column=2, sticky='w', padx=4, pady=2)

        # 3. Row 1: the model list and the refresh button.
        #    The combobox is kept in a field: refresh_master_chief_models will fill it later.
        ttk.Label(frame, text='Model:').grid(row=1, column=0, sticky='w', padx=4, pady=2)
        self.master_chief_combo = ttk.Combobox(frame, textvariable=self.vars['master_chief_model'])
        self.master_chief_combo.grid(row=1, column=1, sticky='ew', padx=4, pady=2)
        ttk.Button(frame, text='Refresh list',
                   command=self.refresh_master_chief_models).grid(row=1, column=2, sticky='w', padx=4, pady=2)

        # 4. Rows 2-3: fields used only for "Own API".
        ttk.Label(frame, text='API address:').grid(row=2, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frame, textvariable=self.vars['master_chief_url']).grid(
            row=2, column=1, sticky='ew', padx=4, pady=2)
        ttk.Label(frame, text='Key variable:').grid(row=3, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frame, textvariable=self.vars['master_chief_key_env']).grid(
            row=3, column=1, sticky='ew', padx=4, pady=2)

        # 5. Row 4: the API key itself. It is not part of the form (never written to the
        #    choice file), so it has its own variable. show='*' hides the characters.
        self.master_chief_key = tk.StringVar()
        ttk.Label(frame, text='API key:').grid(row=4, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frame, textvariable=self.master_chief_key, show='*').grid(
            row=4, column=1, sticky='ew', padx=4, pady=2)

    def build_executor_block(self):
        """Frame "Executors (executor, executor-fast)": two radio buttons bound to
        vars['exec_source'], a combobox for exec_instance with "Refresh list"
        (refresh_lmstudio), entries for exec_url, exec_model, exec_key_env and the key."""
        # 1. The frame, placed in row 1 of the window (row 0 is the Master Chief frame).
        frame = ttk.LabelFrame(self.window, text='Executors (executor, executor-fast)')
        frame.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        frame.columnconfigure(1, weight=1)

        # 2. Two radio buttons sharing one variable: LM Studio or an own API.
        source = self.vars['exec_source']
        ttk.Radiobutton(frame, text='LM Studio (loaded model)', variable=source,
                        value=EXEC_LMSTUDIO).grid(row=0, column=0, sticky='w', padx=4, pady=2)
        ttk.Radiobutton(frame, text='Own API', variable=source,
                        value=EXEC_API).grid(row=0, column=1, sticky='w', padx=4, pady=2)

        # 3. Row 1: the loaded LM Studio model and the refresh button.
        #    Kept in a field: refresh_lmstudio will fill it later.
        ttk.Label(frame, text='LM Studio model:').grid(row=1, column=0, sticky='w', padx=4, pady=2)
        self.exec_instance_combo = ttk.Combobox(frame, textvariable=self.vars['exec_instance'])
        self.exec_instance_combo.grid(row=1, column=1, sticky='ew', padx=4, pady=2)
        ttk.Button(frame, text='Refresh list',
                   command=self.refresh_lmstudio).grid(row=1, column=2, sticky='w', padx=4, pady=2)

        # 4. Rows 2-4: fields used only for "Own API".
        ttk.Label(frame, text='API address:').grid(row=2, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frame, textvariable=self.vars['exec_url']).grid(
            row=2, column=1, sticky='ew', padx=4, pady=2)
        ttk.Label(frame, text='API model:').grid(row=3, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frame, textvariable=self.vars['exec_model']).grid(
            row=3, column=1, sticky='ew', padx=4, pady=2)
        ttk.Label(frame, text='Key variable:').grid(row=4, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frame, textvariable=self.vars['exec_key_env']).grid(
            row=4, column=1, sticky='ew', padx=4, pady=2)

        # 5. Row 5: the API key itself, with its own variable (never written to the file).
        self.exec_key = tk.StringVar()
        ttk.Label(frame, text='API key:').grid(row=5, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frame, textvariable=self.exec_key, show='*').grid(
            row=5, column=1, sticky='ew', padx=4, pady=2)

    def build_buttons(self):
        """Bottom row: "Save" (on_save), "Apply" (on_apply), "Reset" (on_reset)
        and a status label that shows the last result."""
        # 1. A plain frame (no title) in row 2 of the window, under the two blocks.
        frame = ttk.Frame(self.window)
        frame.grid(row=2, column=0, sticky='ew', padx=8, pady=4)
        frame.columnconfigure(3, weight=1)  # empty column 3 takes the free width, so the buttons stay on the left

        # 2. Three buttons in one row. command is a reference to a method, without brackets.
        ttk.Button(frame, text='Save', command=self.on_save).grid(row=0, column=0, padx=4, pady=2)
        ttk.Button(frame, text='Apply', command=self.on_apply).grid(row=0, column=1, padx=4, pady=2)
        ttk.Button(frame, text='Reset', command=self.on_reset).grid(row=0, column=2, padx=4, pady=2)

        # 3. The status line: a label bound to its own variable. Every handler writes
        #    the result into self.status, and the label shows it at once.
        self.status = tk.StringVar(value='Ready')
        ttk.Label(frame, textvariable=self.status, wraplength=560, justify='left').grid(
            row=1, column=0, columnspan=4, sticky='w', padx=4, pady=4)

    def read_form(self) -> dict:
        """Current values of all variables as a plain form dictionary."""
        return {key: var.get().strip() for key, var in self.vars.items()}

    def fill_form(self, form: dict):
        """Put the values of a form dictionary into the window variables."""
        for key, value in form.items():
            self.vars[key].set(value)

    def load_form(self):
        """Fill the variables from the saved choice file (models_choices_configurator.load_choices + choices_to_form).
        On a broken file show the error in the status label and keep EMPTY_FORM."""
        try:
            data = models_choices_configurator.load_choices(self.root)
        except ValueError as error:
            self.status.set(f'The saved choice was not loaded: {error}')
            return
        self.fill_form(choices_to_form(data))
        self.status.set('Saved choice loaded' if data else 'No saved choice: defaults are shown')

    def typed_or_saved_key(self, key_var, env_name: str) -> str:
        """The key typed in the window, or else the value of the saved variable env_name."""
        typed = key_var.get().strip()
        if typed:
            return typed
        return os.environ.get(env_name, '')

    def refresh_master_chief_models(self):
        """Fill the Master Chief combobox: sources.opencode_models() for MASTER_CHIEF_OPENCODE,
        sources.api_models(url, key) for MASTER_CHIEF_API. Errors go to the status label."""
        form = self.read_form()
        source = form['master_chief_source']
        try:
            if source == MASTER_CHIEF_OPENCODE:
                models = sources.opencode_models()
            elif source == MASTER_CHIEF_API:
                key = self.typed_or_saved_key(self.master_chief_key, form['master_chief_key_env'])
                models = sources.api_models(form['master_chief_url'], key)
            else:
                self.status.set('Choose "Model from OpenCode" or "Own API" to get a list of models')
                return
        except ValueError as error:
            self.status.set(f'Model list was not received: {error}')
            return
        self.master_chief_combo['values'] = models
        self.status.set(f'Models found: {len(models)}')

    def refresh_lmstudio(self):
        """Fill the instance combobox from sources.lmstudio_instances()."""
        try:
            pairs = sources.lmstudio_instances()
        except ValueError as error:
            self.status.set(f'LM Studio did not answer: {error}')
            return
        self.exec_instance_combo['values'] = [instance_id for instance_id, name in pairs]
        if pairs:
            names = ', '.join(name for instance_id, name in pairs)
            self.status.set(f'Loaded in LM Studio: {names}')
        else:
            self.status.set('No model is loaded in LM Studio. Load one and press Refresh list again')

    def save_typed_key(self, key_var, env_name: str) -> str:
        """Save a typed key into the user variable env_name. Returns a note for the status line."""
        value = key_var.get().strip()
        if not value:
            return ''
        keys.save_user_variable(env_name, value)
        key_var.set('')  # the key is saved; do not keep it in the window
        return f'{env_name} = {keys.mask(value)}'

    def on_save(self) -> bool:
        """Save typed keys (keys.save_user_variable), then form_to_choices + models_choices_configurator.save_choices.
        Show "Saved: <path>" or the error text. Never show a key: use keys.mask.
        Returns True when everything was saved."""
        form = self.read_form()
        try:
            choices = form_to_choices(form)  # check the form first: nothing is saved on an error
            notes = [self.save_typed_key(self.master_chief_key, form['master_chief_key_env']),
                     self.save_typed_key(self.exec_key, form['exec_key_env'])]
            path = models_choices_configurator.save_choices(self.root, choices)
        except (ValueError, OSError) as error:
            self.status.set(f'Not saved: {error}')
            return False
        saved_keys = [note for note in notes if note]
        text = f'Saved: {path}'
        if saved_keys:
            text += '\nKeys saved: ' + ', '.join(saved_keys)
        self.status.set(text)
        return True

    def on_apply(self):
        """on_save, then apply_choices; show the exit code and the launcher output."""
        if not self.on_save():
            return  # on_save has already shown the error
        try:
            code, output = apply_choices(self.root)
        except (subprocess.TimeoutExpired, OSError) as error:
            self.status.set(f'The launcher did not run: {error}')
            return
        result = 'Applied' if code == 0 else f'The launcher failed with exit code {code}'
        self.status.set(f'{result}\n{output.strip()}')

    def on_reset(self):
        """models_choices_configurator.reset_choices, then fill the form with EMPTY_FORM."""
        try:
            removed = models_choices_configurator.reset_choices(self.root)
        except OSError as error:
            self.status.set(f'Not reset: {error}')
            return
        self.fill_form(EMPTY_FORM)
        self.master_chief_key.set('')
        self.exec_key.set('')
        if removed:
            self.status.set('Choice file deleted: the defaults are used again')
        else:
            self.status.set('Nothing to reset: the defaults are already used')


def main() -> int:
    """Create the window and run the event loop until it is closed."""
    if tk is None:
        print('tkinter is not available, cannot run the configurator window.')
        return 1
    window = tk.Tk()
    window.title('Model Configurator')
    window.resizable(True, False)
    app = ConfiguratorApp(window)
    window.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
