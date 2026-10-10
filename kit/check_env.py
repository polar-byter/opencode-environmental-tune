# -*- coding: utf-8 -*-
"""
check_env.py — agentic environment checker.

Checks:
  1. Syntax of the opencode.jsonc config (JSON with comments).
  2. LM Studio API (http://127.0.0.1:1234/v1) online.
  3. Language model instances already loaded in LM Studio.
  4. A trial request to one unambiguously selected loaded instance.

Usage:
  python check_env.py
"""
import json
import argparse
#regex we need for stripping comments and trailing commas from JSONC
import re 
# sys is used to reconfigure the console output encoding on Windows.
import sys
import urllib.request
import urllib.error
from pathlib import Path

try:
    from .lmstudio_models import base_url, configured_model, loaded_models, select_model
except ImportError:
    from lmstudio_models import base_url, configured_model, loaded_models, select_model

# Windows-console often works with cp1251 or cp866, which breaks UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass 

# my local LM Studio server (Developer -> Start Server) is running on
LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
# opencode.jsonc lives in the project root, one level above kit/.
# we store this script in kit/ so that it can be run from any working directory.
CONFIG_PATH = Path(__file__).resolve().parent.parent / "opencode.jsonc"

# Matches either a JSON string (kept) or a comment (removed).
# The string alternative comes first, so "//" inside a string is never a comment.
_STRING_OR_COMMENT = re.compile(
    r'("(?:\\.|[^"\\])*")'  # group 1: a full string "abcdef..etc", escapes included
    r"|//[^\r\n]*"          # or a // line comment
    r"|/\*.*?\*/",          # or a /* block comment */
    re.DOTALL,
)


def strip_jsonc(text: str) -> str:
    # To convert jsonc(comments) into plain json
    text = _STRING_OR_COMMENT.sub(lambda m: m.group(1) or "", text)
    #remove commas before "]"
    return re.sub(r",(\s*[}\]])", r"\1", text)


def check_config() -> bool:
    """Step 1: To see if is opencode.jsonc valid?"""
    print("=" * 60)
    print("[1] Checking opencode.jsonc")
    print("=" * 60)
    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"  File not found: {CONFIG_PATH}")
        return False
    try:
        strip_json_data = strip_jsonc(raw)
        result_config_data = json.loads(strip_json_data)
    except json.JSONDecodeError as e:
        print(f"  JSON error: {e}")
        return False
    
    print(f"     json data is valid; \r\n size: ({len(raw)} chars)")
    print(f"     model (Master Chief):       {result_config_data.get('model', '—')}")
    print(f"     default_agent:       {result_config_data.get('default_agent', '—')}")
    lm = result_config_data.get("providers", {}).get("lmstudio", {})
    print(f"     lmstudio.baseURL:    {lm.get('settings', {}).get('baseURL', 'default')}")
    models = lm.get("models", {})
    print(f"     local aliases:       {', '.join(models.keys()) if models else '— (dynamic discovery)'}")
    agents = result_config_data.get("agents", {})
    for name, cfg in agents.items():
        model = cfg.get("model", "inherits session")
        mode = cfg.get("mode", "primary")
        print(f"     agent {name:14s}: mode={mode:<9s} model={model}")
    return True



def http_get_json(url: str):
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict, timeout: float = 180):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout = timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_lmstudio(base: str = LMSTUDIO_BASE) -> list:
    """Step 2: List already loaded language model instances.
    Returns loaded instances from the native API
    or an empty list if the server is offline.
    """

    print()
    print("=" * 60)
    print("[2] LM Studio API")
    print("=" * 60)
    try:
        models = loaded_models(base)
        print(f" Server responds ({len(models)} loaded language model instances):")
        for m in models:
            print(f"    - {m.id}")
        return models
    except urllib.error.URLError as e:
        print(f"  No connection: {e}")
        print("   Start LM Studio and enable the local server (Developer -> Start Server).")
        return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


# Main test: use an already loaded instance, never a downloaded-model fallback.
#Returns True only when the model really answered.
def live_test(models: list, preferred: str | None = None, explicit: str | None = None,
              base: str = LMSTUDIO_BASE) -> bool:
    print()
    print("=" * 60)
    print("[3] Live generation test (chat/completions)")
    print("=" * 60)
    try:
        target = select_model(models, preferred, explicit).id
    except ValueError as error:
        print(f"  {error}")
        return False
    print(f"  Model: {target}")
    payload = {
        "model": target,
        # local models reasoning_tokens; create a budget enough for the answer.
        "messages": [{"role": "user", "content": "Reply with exactly one word: OK"}],
        "max_tokens": 200,
        "temperature": 0.0,
    }
    try:
        resp = http_post_json(f"{base}/chat/completions", payload)
        content = resp["choices"][0]["message"]["content"].strip()
        finish = resp["choices"][0].get("finish_reason", "?")
        print(f"  Model answer: «{content}» (finish_reason={finish})")
        print("   Local generation works!")
        return True
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        print("   The model may not be loaded in LM Studio (press Load).")
    except Exception as e:
        print(f"  Error: {e}")
    return False


def main(argv=None):
    #Runs all checks in order and returns an exit code: 0 = ok, 1 = problems.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', help='already loaded LM Studio instance ID')
    args = parser.parse_args(argv)
    print("🧪 Checking agentic environment\n")
    ok_config = check_config()
    if not ok_config:
        return 1
    config = json.loads(strip_jsonc(CONFIG_PATH.read_text(encoding='utf-8')))
    base = base_url(config)
    models = check_lmstudio(base)
    live_ok = live_test(models, configured_model(config), args.model, base)
    print()
    print("=" * 60)
    is_ready_to_use = ok_config and bool(models) and live_ok
    summary = "ready for use" if (is_ready_to_use) else "test failed"
    print(f"Result: {summary}")
    return 0 if (is_ready_to_use) else 1

if __name__ == "__main__":
    sys.exit(main())
