"""It selects an already loaded LM Studio instance
without changing its load settings."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

DEFAULT_BASE = 'http://127.0.0.1:1234/v1'


@dataclass(frozen=True)
class LoadedModel:
    """
    Represents a loaded LM Studio model instance.
    The instance ID is unique among loaded instances,
    while the model key may be shared by multiple instances
    """

    id: str
    key: str
    name: str


def base_url(config: dict) -> str:
    """Return the OpenAI-compatible endpoint configured for LM Studio."""
    return config.get('providers', {}).get('lmstudio', {}).get('settings', {}).get('baseURL', DEFAULT_BASE).rstrip('/')


def loaded_models(base: str = DEFAULT_BASE) -> list[LoadedModel]:
    """Read native API v1;
        it lists loaded instances and their model keys.
        It does not return models that are only downloaded but not loaded.
    """
    origin = base.rstrip('/')
    if origin.endswith('/v1'):
        origin = origin[:-3]
    request = urllib.request.Request(origin + '/api/v1/models', headers={'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get('models'), list):
        raise ValueError('Unsupported LM Studio response: expected native /api/v1/models. Update LM Studio; no automatic fallback to downloaded models.')
    model_list_result = {}
    for model in data['models']:
        if not isinstance(model, dict) or model.get('type') != 'llm':
            continue
        if not isinstance(model.get('key'), str) or not isinstance(model.get('loaded_instances'), list):
            raise ValueError('Unsupported LM Studio model entry: key and loaded_instances are required')
        for instance in model['loaded_instances']:
            if not isinstance(instance, dict) or not isinstance(instance.get('id'), str) or not instance['id']:
                raise ValueError('LM Studio returned a loaded instance without an ID')
            # The instance ID is unique, while the model key may be shared by multiple instances.
            item_loaded_model = LoadedModel(instance['id'], model['key'], model.get('display_name') or model['key'])
            if item_loaded_model.id in model_list_result and model_list_result[item_loaded_model.id] != item_loaded_model:
                raise ValueError('LM Studio returned conflicting loaded instance IDs')
            model_list_result[item_loaded_model.id] = item_loaded_model
    return list(model_list_result.values())


def configured_model(config: dict) -> str | None:
    """Resolve the executor alias to a preferred model key; it need not be loaded.
       it returns None if the executor is not configured or not an LM Studio model.
       It reads only the config and does not check whether the model is loaded:
       select_model() uses the result as a soft preference.
    """
    ref = config.get('agents', {}).get('executor', {}).get('model')
    if not isinstance(ref, str) or not ref:
        return None
    provider, separator, alias = ref.partition('/')
    if separator and provider != 'lmstudio':
        return None
    alias = alias if separator else ref
    entry = config.get('providers', {}).get('lmstudio', {}).get('models', {}).get(alias, {})
    return entry.get('modelID') or alias


def select_model(models: list[LoadedModel], preferred_model: str | None = None,
                 explicit_model: str | None = None) -> LoadedModel:
    """Choose an instance only when it is unambiguously identifiable.
    explicit_model comes from the user (--model) and takes precedence over
    preferred_model, which comes from the configuration.
    Both are matched by instance ID first, then by model key.
    - No loaded models: error.
    - explicit_model must match exactly one loaded instance, otherwise error.
    - preferred_model is used if it matches exactly one instance; several matches
      are an error, but no match is not: the choice falls through.
    - Otherwise the only loaded instance is used; several loaded instances are an error.
    """
    if not models:
        raise ValueError('No language model is loaded. Load one in LM Studio with your settings and start its server.')
    target = explicit_model or preferred_model
    if target:
        exact = [m for m in models if m.id == target]
        matches = exact or [m for m in models if m.key == target]
        if len(matches) == 1:
            return matches[0]
        if matches or explicit_model:
            choices = ', '.join(m.id for m in (matches or models))
            raise ValueError(f'Model {target!r} does not identify one loaded instance. Choose --model with an instance ID. Loaded: {choices}')
    if len(models) == 1:
        return models[0]
    raise ValueError('Several language models are loaded. Choose --model with an instance ID: ' + ', '.join(m.id for m in models))
