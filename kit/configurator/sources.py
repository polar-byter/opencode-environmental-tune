"""Lists of models the user can choose from.

Three sources:
- OpenCode itself: the command "opencode models" prints every model it can use
  (OpenCode Go, a ChatGPT subscription connected with /connect, other providers);
- an own OpenAI-compatible API: GET <baseURL>/models with the key;
- LM Studio: instances that are already loaded (kit/lmstudio_models.py does the work).

The parse_* functions are pure: text or a dict in, a list out. They are tested without
network. The other functions only fetch data and hand it to a parse_xxx function.

"""
from __future__ import annotations

import json
import subprocess
import urllib.request
import re
import urllib.error
from .. import lmstudio_models
from ..run_opencode import find_opencode

# this regex can be explained as: 
# "a string that starts with a non-slash character, 
# followed by one or more groups of a slash 
# and a non-slash character".
PARSE_LINE_PATTERN = re.compile(r'^[^/\s]+(/[^/\s]+)+')
TIMEOUT = 30  
# seconds for any outside call, before it is considered a failure. The user can change it with --timeout.

# Step 3. Pure parsing
def parse_opencode_models(text: str) -> list[str]:
    """Convert the output of opencode models into a list of model references.

    Every useful line starts with a reference like "openai/gpt-6.1-sol"; 
    anything after the first space on that line is ignored. 
    Lines without "/" (headers, empty lines, messages) are skipped.
    Returns:
        Unique references, sorted alphabetically.
    """
    input_lines = text.splitlines()
    model_refs_list = []
    model_refs_list = {line.split()[0] for line in input_lines if PARSE_LINE_PATTERN.match(line)}
    return sorted(model_refs_list)

def parse_api_models(data: dict) -> list[str]:
    """Take model names from an OpenAI-style answer of GET /models.
    Expected shape: {"data": [{"id": "model-a", ...}, {"id": "model-b", ...}]}.
    Returns:
        Sorted unique ids. Entries without a string "id" are skipped.
    Raises:
        ValueError: there is no "data" list (the address is probably wrong).
    """
    data_list = data.get("data")
    if not isinstance(data_list, list):
        raise ValueError('the "data" key is missing or is not a list')
    model_ids = [
        item["id"] for item in data_list if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    unique_model_ids = set(model_ids)
    sorted_model_ids = sorted(unique_model_ids)
    return sorted_model_ids

# --- Step 4. Fetching ----------------------------------------------------------

def opencode_models(command: str = 'opencode') -> list[str]:
    """Ask OpenCode which models it can use.
    Runs "<opencode> models" without a shell, waits at most TIMEOUT seconds and parses
    the output with parse_opencode_models.
    Raises:
        ValueError: OpenCode is not found (find_opencode raises it) or exits with an error;
                    the message includes the error text of OpenCode.
    """
    exe_opencode_util = find_opencode(command)
    try:
        process_result = subprocess.run(
            [exe_opencode_util, 'models'],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            encoding='utf-8'
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError(f'"opencode models" did not answer within {TIMEOUT} seconds') from error
    except OSError as error:
        raise ValueError(f'could not start OpenCode ({exe_opencode_util}): {error}') from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ValueError(f'failed to fetch models from OpenCode: {error}') from error

    if process_result.returncode != 0:
        details = process_result.stderr.strip() or process_result.stdout.strip() or 'no error text'
        raise ValueError(f'"opencode models" failed with exit code {process_result.returncode}: {details}')

    output_text = process_result.stdout
    
    return parse_opencode_models(output_text)

def api_models(base_url: str, api_key: str) -> list[str]:
    """Ask an own API for its models: GET <base_url>/models with "Authorization: Bearer <key>".
    Returns:
        parse_api_models of the JSON answer.
    The key is used only for this request and is never printed.
    """
    url = base_url.rstrip('/') + '/models'
    headers = {'Authorization': f'Bearer {api_key}'}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.load(response)
    except urllib.error.URLError as error:
        raise ValueError(f'failed to fetch models from {url}: {error}') from error
    except json.JSONDecodeError as error:
        raise ValueError(f'failed to parse JSON from {url}: {error}') from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ValueError(f'failed to fetch models from {url}: {error}') from error
    
    return parse_api_models(data)



def lmstudio_instances(base: str = lmstudio_models.DEFAULT_BASE) -> list[tuple[str, str]]:
    """Loaded LM Studio instances as (instance id, display name) pairs, sorted by name."""
    # ПОДСКАЗКА: всё уже умеет lmstudio_models.loaded_models(base). Она возвращает
    #   объекты LoadedModel с полями .id и .name. Осталось превратить их в пары.
    # ПОДСКАЗКА: пара (кортеж) пишется в круглых скобках: (model.id, model.name).
    # ПОДСКАЗКА: сортировка по второму элементу: sorted(pairs, key=lambda pair: pair[1]).
    raise NotImplementedError('step 4.3: lmstudio_instances')
