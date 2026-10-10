"""Model settings in the browser: the same logic as the tkinter window, without the window.

The web form uses exactly the form dictionary of kit/configurator/app.py (EMPTY_FORM keys)
plus two optional fields for typed keys: "master_chief_key" and "exec_key". All checks stay
in the configurator modules; this module only connects them to JSON requests.

Security rules (the page is local, but keys are secrets):
- A key value never goes into a response, a log line or the choice file. Responses carry
  only {"set": bool, "masked": keys.mask(value)} for a variable name.
- A key is saved only through keys.save_user_variable, after the form passed form_to_choices.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..configurator import app, keys, models_choices_configurator, sources

KEY_FIELDS = (('master_chief_key', 'master_chief_key_env'), ('exec_key', 'exec_key_env'))


def key_state(name: str) -> dict:
    """{"name": name, "set": keys.key_is_set(name), "masked": keys.mask(value)}, where
    value = keys.read_user_variable(name) or os.environ.get(name) or "" (the same two places
    key_is_set looks at). The value is read only to mask it. An invalid variable name
    (keys.is_valid_env_name is False) -> {"name": name, "set": False, "masked": ""} without
    reading anything."""
    raise NotImplementedError('dashboard step 4.1: key_state')


def get_settings(root: Path) -> dict:
    """Current settings of one project for the form.

    {"form": app.choices_to_form(load_choices(root)),
     "keys": {"master_chief": key_state(form master_chief_key_env),
              "executor": key_state(form exec_key_env)}}
    A broken choice file -> {"form": dict(app.EMPTY_FORM), "keys": ..., "error": "<message>"}.
    """
    raise NotImplementedError('dashboard step 4.2: get_settings')


def clean_form(data: dict) -> dict:
    """The form part of a request: a copy of app.EMPTY_FORM updated with the values of
    data whose keys are in EMPTY_FORM. Every value must be a str (else ValueError naming
    the field); values are stripped. Unknown keys and the typed key fields are dropped."""
    raise NotImplementedError('dashboard step 4.3: clean_form')


def save_settings(root: Path, data: dict) -> dict:
    """Save button: check the form, then store typed keys, then write the choice file.

    Order matters: nothing is stored when the form is invalid.
      1. form = clean_form(data); choices = app.form_to_choices(form)   (ValueError -> raise)
      2. for each (key_field, env_field) in KEY_FIELDS: a non-blank str data[key_field] is
         saved with keys.save_user_variable(form[env_field], value.strip())
      3. path = models_choices_configurator.save_choices(root, choices)
    Returns {"saved": str(path), "keys": [names of the saved variables]}.
    """
    raise NotImplementedError('dashboard step 4.4: save_settings')


def apply_settings(root: Path, data: dict) -> dict:
    """Apply button: save_settings, then app.apply_choices(root).
    Returns {"saved": ..., "keys": ..., "code": exit code, "output": launcher output}."""
    raise NotImplementedError('dashboard step 4.5: apply_settings')


def reset_settings(root: Path) -> dict:
    """Reset button: {"removed": models_choices_configurator.reset_choices(root)}.
    The overlay is not rebuilt here, the same as in the window (see the vault note 19)."""
    raise NotImplementedError('dashboard step 4.6: reset_settings')


def model_list(source: str, base_url: str = '', key_env: str = '') -> list[str]:
    """Models for a combobox.

    source "opencode" -> sources.opencode_models();
    "lmstudio" -> [instance id for id, name in sources.lmstudio_instances()];
    "api" -> sources.api_models(base_url, key) where key = keys.read_user_variable(key_env);
             a missing key raises ValueError("<key_env> is not set").
    Unknown source -> ValueError. Errors of sources (ValueError) are passed through.
    """
    raise NotImplementedError('dashboard step 4.7: model_list')
