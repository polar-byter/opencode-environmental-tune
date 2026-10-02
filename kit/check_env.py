# -*- coding: utf-8 -*-
"""
check_env.py — agentic environment checker.

Checks:
  1. Syntax of the opencode.jsonc config (JSON with comments).
  2. LM Studio API (http://127.0.0.1:1234/v1) online.
  3. List of local models visible to LM Studio.
  4. Test scenario for requesting the first generative model found.

Usage:
  python check_env.py
"""
import json
#regex we need for stripping comments and trailing commas from JSONC
import re 
# sys is used to reconfigure the console output encoding on Windows.
import sys
import urllib.request
import urllib.error
from pathlib import Path

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

# embedding models are for vectorization / rag, not for generation, so we skip them in the live test.
EMBED_ONLY_SUBSTRINGS = ("embed", "embedding")

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
    """Step 1: is opencode.jsonc valid?"""
    print("=" * 60)
    print("[1] Checking opencode.jsonc")
    print("=" * 60)
    try:
        raw = open(CONFIG_PATH, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"  File not found: {CONFIG_PATH}")
        return False
    try:
        json.loads(strip_jsonc(raw))
        print(f"  JSON is valid ({len(raw)} chars)")
        data = json.loads(strip_jsonc(raw))
        print(f"     model (brain):       {data.get('model', '—')}")
        print(f"     default_agent:       {data.get('default_agent', '—')}")
        lm = data.get("providers", {}).get("lmstudio", {})
        print(f"     lmstudio.baseURL:    {lm.get('settings', {}).get('baseURL', 'default')}")
        models = lm.get("models", {})
        print(f"     local aliases:       {', '.join(models.keys()) if models else '— (dynamic discovery)'}")
        agents = data.get("agents", {})
        for name, cfg in agents.items():
            model = cfg.get("model", "inherits session")
            mode = cfg.get("mode", "primary")
            print(f"     agent {name:14s}: mode={mode:<9s} model={model}")
        return True
    except json.JSONDecodeError as e:
        print(f"  JSON error: {e}")
        return False


def http_get_json(url: str):
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))

"""
    Returns a list of model IDs visible to LM Studio
    or an empty list if the server is not reachable.
"""   
def check_lmstudio() -> list:
    print()
    print("=" * 60)
    print("[2] LM Studio API")
    print("=" * 60)
    try:
        data = http_get_json(f"{LMSTUDIO_BASE}/models")
        models = [m["id"] for m in data.get("data", [])]
        print(f" Server responds ({len(models)} models):")
        for m in models:
            print(f"    - {m}")
        return models
    except urllib.error.URLError as e:
        print(f"  No connection: {e}")
        print("   Start LM Studio and enable the local server (Developer -> Start Server).")
        return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


#Main test: send a simple prompt to the first generative model found.
def live_test(models: list):
    print()
    print("=" * 60)
    print("[3] Live generation test (chat/completions)")
    print("=" * 60)
    # keep only models that are not embeddings
    candidates = [m for m in models if not any(s in m.lower() for s in EMBED_ONLY_SUBSTRINGS)]

    if not candidates:
        print("  No generative models found — live test skipped.")
        return
    
    target = candidates[0]
    print(f"  Model: {target}")
    payload = {
        "model": target,
        # local models reasoning_tokens; create a budget enough for the answer.
        "messages": [{"role": "user", "content": "Reply with exactly one word: OK"}],
        "max_tokens": 200,
        "temperature": 0.0,
    }
    try:
        resp = http_post_json(f"{LMSTUDIO_BASE}/chat/completions", payload)
        content = resp["choices"][0]["message"]["content"].strip()
        finish = resp["choices"][0].get("finish_reason", "?")
        print(f"  Model answer: «{content}» (finish_reason={finish})")
        print("   Local generation works!")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        print("   The model may not be loaded in LM Studio (press Load).")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    #Runs all checks in order and returns an exit code: 0 = ok, 1 = problems.
    print("🧪 Checking agentic environment\n")
    ok_config = check_config()
    models = check_lmstudio()
    live_test(models)
    print()
    print("=" * 60)
    summary = "ready for use" if (ok_config and models) else "test failed"
    print(f"Result: {summary}")
    return 0 if (ok_config and models) else 1

if __name__ == "__main__":
    sys.exit(main())
