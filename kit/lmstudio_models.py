"""Select an already loaded LM Studio instance without changing its load settings."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

DEFAULT_BASE = 'http://127.0.0.1:1234/v1'


@dataclass(frozen=True)
class LoadedModel:
    id: str
    key: str
    name: str


def base_url(config: dict) -> str:
    """Return the OpenAI-compatible endpoint configured for LM Studio."""
    return config.get('providers', {}).get('lmstudio', {}).get('settings', {}).get('baseURL', DEFAULT_BASE).rstrip('/')


def loaded_models(base: str = DEFAULT_BASE) -> list[LoadedModel]:
    """Read native API v1; downloaded but unloaded models are never candidates."""
    origin = base.rstrip('/')
    if origin.endswith('/v1'):
        origin = origin[:-3]
    request = urllib.request.Request(origin + '/api/v1/models', headers={'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get('models'), list):
        raise ValueError('Unsupported LM Studio response: expected native /api/v1/models. Update LM Studio; no automatic fallback to downloaded models.')
    result = {}
    for model in data['models']:
        if not isinstance(model, dict) or model.get('type') != 'llm':
            continue
        if not isinstance(model.get('key'), str) or not isinstance(model.get('loaded_instances'), list):
            raise ValueError('Unsupported LM Studio model entry: key and loaded_instances are required')
        for instance in model['loaded_instances']:
            if not isinstance(instance, dict) or not isinstance(instance.get('id'), str) or not instance['id']:
                raise ValueError('LM Studio returned a loaded instance without an ID')
            item = LoadedModel(instance['id'], model['key'], model.get('display_name') or model['key'])
            if item.id in result and result[item.id] != item:
                raise ValueError('LM Studio returned conflicting loaded instance IDs')
            result[item.id] = item
    return list(result.values())


def configured_model(config: dict) -> str | None:
    """Resolve the executor alias to a preferred model key; it need not be loaded."""
    ref = config.get('agents', {}).get('executor', {}).get('model')
    if not isinstance(ref, str) or not ref:
        return None
    provider, separator, alias = ref.partition('/')
    if separator and provider != 'lmstudio':
        return None
    alias = alias if separator else ref
    entry = config.get('providers', {}).get('lmstudio', {}).get('models', {}).get(alias, {})
    return entry.get('modelID') or alias


def select_model(models: list[LoadedModel], preferred: str | None = None,
                 explicit: str | None = None) -> LoadedModel:
    """Choose an instance unambiguously. An explicit unloaded model is an error."""
    if not models:
        raise ValueError('No language model is loaded. Load one in LM Studio with your settings and start its server.')
    target = explicit or preferred
    if target:
        exact = [m for m in models if m.id == target]
        matches = exact or [m for m in models if m.key == target]
        if len(matches) == 1:
            return matches[0]
        if matches or explicit:
            choices = ', '.join(m.id for m in (matches or models))
            raise ValueError(f'Model {target!r} does not identify one loaded instance. Choose --model with an instance ID. Loaded: {choices}')
    if len(models) == 1:
        return models[0]
    raise ValueError('Several language models are loaded. Choose --model with an instance ID: ' + ', '.join(m.id for m in models))
