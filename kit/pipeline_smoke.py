# -*- coding: utf-8 -*-
"""
pipeline_smoke.py — optional offline smoke test of the brain → executor → review flow.

It doesn't use Open Code to talks to LM Studio directly, so you can check that the
local executor model can implement a spec-commented skeleton.

Flow:
  1. Write a skeleton with spec comments and tests into a temporary directory.
  2. Ask the executor model (LM Studio) to implement the bodies.
  3. Run the tests and report.

The executor model is resolved from opencode.jsonc:
  agents.executor.model = "lmstudio/<alias>"  →  providers.lmstudio.models[<alias>].modelID
This preference is used only if that model is already loaded. Otherwise a sole
loaded language model is used. Choose --model <loaded-instance-id> when ambiguous.

Usage:
  py pipeline_smoke.py
  py pipeline_smoke.py --model spark-x2.5-4b
  py pipeline_smoke.py --keep        # keep the temp dir and print its path
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
from pathlib import Path

# Reuse the JSONC and HTTP helpers from check_env.py (shipped together).
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from check_env import CONFIG_PATH, LMSTUDIO_BASE, http_post_json, strip_jsonc  # noqa: E402
from lmstudio_models import base_url, configured_model, loaded_models, select_model

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REQUEST_TIMEOUT = 300


# ── model resolution ────────────────────────────────────────────────

def load_config(path: str | Path = CONFIG_PATH) -> dict:
    """
    Reads opencode.jsonc (JSONC) and returns the parsed dict.

    Returns {} if the file is missing, unreadable, or invalid. Never raises.
    """
    config_path = Path(path)
    if not config_path.exists():
        return {}
    try:
        return json.loads(strip_jsonc(config_path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def resolve_executor_model(config: dict, override: str | None = None) -> str | None:
    """
    Resolves the LM Studio model ID for the executor agent.

    Args:
    - config: parsed opencode.jsonc.
    - override: explicit model id; returned as-is when provided.

    Returns:
    - The real LM Studio model ID from the alias map, e.g.
      "qwen3.8-27b-...-max-mtp" for "lmstudio/qwen3-27b-coder".
    - The raw alias when it is not found in the map (it may already be a real id).
    - None when the executor model is absent or not an lmstudio model.
    """
    if override:
        return override
    model_ref = config.get("agents", {}).get("executor", {}).get("model")
    if not model_ref:
        return None
    if "/" not in model_ref:
        return model_ref
    provider, _, alias = model_ref.partition("/")
    if provider != "lmstudio":
        return None
    models = config.get("providers", {}).get("lmstudio", {}).get("models", {})
    entry = models.get(alias)
    if isinstance(entry, dict) and entry.get("modelID"):
        return entry["modelID"]
    return alias


# ── the demo fixture (brain side) ───────────────────────────────────

def brain_skeleton_app() -> str:
    """Skeleton of the module under test: signatures + spec comments + placeholder bodies."""
    return '''# -*- coding: utf-8 -*-
"""calculator.py — percent/discount. Skeleton: brain. Implementation: executor."""


def percent(part: float, whole: float) -> float:
    """
    How many percent part is of whole.

    Spec:
    1. whole == 0 — return 0.0, do not raise.
    2. Otherwise return (part / whole) * 100.
    3. Round to 2 decimals (round(x, 2)).
    4. Standard library only.
    """
    # TODO(executor): implement per spec
    raise NotImplementedError("implement me")


def discount(price: float, percent_off: float) -> float:
    """
    Price after percent_off discount.

    Spec:
    1. Price never below 0: discount above 100% is clamped.
    2. Otherwise return price - price * percent_off / 100.
    3. Round to 2 decimals.
    """
    # TODO(executor): implement per spec
    raise NotImplementedError("implement me")
'''


def brain_skeleton_tests() -> str:
    """Tests written by the brain against the skeleton. They fail until implemented."""
    return '''# -*- coding: utf-8 -*-
"""test_calculator.py — unit tests. Skeleton: brain. Run: brain."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from calculator import percent, discount


class TestPercent(unittest.TestCase):
    def test_normal(self):
        self.assertAlmostEqual(percent(25, 100), 25.0)

    def test_fraction(self):
        self.assertAlmostEqual(percent(1, 3), 33.33, places=2)

    def test_zero_denominator(self):
        self.assertEqual(percent(5, 0), 0.0)

    def test_zero_part(self):
        self.assertEqual(percent(0, 10), 0.0)


class TestDiscount(unittest.TestCase):
    def test_normal(self):
        self.assertAlmostEqual(discount(1000, 20), 800.0)

    def test_full_discount(self):
        self.assertEqual(discount(500, 100), 0.0)

    def test_no_discount(self):
        self.assertAlmostEqual(discount(250, 0), 250.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''


# ── executor (LM Studio) ────────────────────────────────────────────

def executor_implement(skeleton: str, model: str, base_url: str = LMSTUDIO_BASE) -> str:
    """
    Asks LM Studio to fill the function bodies per the spec comments.

    Returns the raw model text (may include a ```python fence; use strip_markdown).
    Raises on HTTP or connection errors.
    """
    prompt = (
        "You are the executor. Below is a Python module skeleton with specs in comments.\n"
        "Implement the functions percent and discount strictly per spec.\n"
        "Return the WHOLE file, with implementations. No explanations, no ``` fences.\n\n"
        "=== SKELETON ===\n" + skeleton
    )
    payload = {
        "model": model,
        "max_tokens": 1024,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = http_post_json(f"{base_url}/chat/completions", payload, timeout=REQUEST_TIMEOUT)
    return data["choices"][0]["message"]["content"]


def strip_markdown(code: str) -> str:
    """Removes a ```python ... ``` fence if the model added one."""
    code = code.strip()
    if code.startswith("```"):
        code = code.split("\n", 1)[-1]
        if code.endswith("```"):
            code = code[:-3].rstrip()
    return code.strip()


# ── review (brain side) ─────────────────────────────────────────────

def run_tests(workdir: Path) -> tuple[bool, str]:
    """Runs unittest inside workdir. Returns (ok, combined output)."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, cwd=str(workdir),
    )
    return process.returncode == 0, process.stdout + process.stderr


def build_parser() -> argparse.ArgumentParser:
    """Builds the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="pipeline_smoke.py",
        description="Offline smoke test of the brain -> executor flow via LM Studio.",
    )
    parser.add_argument("--model", help="already loaded LM Studio instance ID")
    parser.add_argument("--keep", action="store_true", help="keep the temp dir and print its path")
    return parser

def run_smoke(workdir: Path, model: str, base: str = LMSTUDIO_BASE) -> int:
    app_dir = workdir / "app"
    tests_dir = workdir / "tests"
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    skeleton = brain_skeleton_app()
    (app_dir / "calculator.py").write_text(skeleton, encoding="utf-8")
    (tests_dir / "test_calculator.py").write_text(brain_skeleton_tests(), encoding="utf-8")
    print(f"Workdir: {workdir}")

    ok_before, _ = run_tests(workdir)
    print(f"Tests before implementation: {'green (unexpected)' if ok_before else 'red (expected)'}")

    print("Asking the executor...")
    try:
        raw = executor_implement(skeleton, model, base)
    except urllib.error.HTTPError as error:
        print(f"HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:300]}")
        return 1
    except Exception as error:  # noqa: BLE001
        print(f"ERROR: {error}")
        return 1

    (app_dir / "calculator.py").write_text(strip_markdown(raw), encoding="utf-8")
    ok_after, output = run_tests(workdir)
    print("-" * 60)
    print(output.strip() or "(no output)")
    print("-" * 60)

    if ok_after:
        print("RESULT: green — the local executor implemented the spec correctly.")
        return 0
    print("RESULT: red — the executor needs a retry or the spec needs to be sharper.")
    return 1


def main(argv=None) -> int:
    """CLI entry point. Returns 0 when tests are green, 1 otherwise."""
    args = build_parser().parse_args(argv)
    print("pipeline smoke test: brain -> executor -> review (offline)")
    print("=" * 60)

    config = load_config()
    base = base_url(config)
    try:
        model = select_model(loaded_models(base), configured_model(config), args.model).id
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}")
        return 1
    print(f"Model: {model}")

    if args.keep:
        workdir = Path(tempfile.mkdtemp(prefix="pipeline_smoke_"))
        print(f"Kept workdir: {workdir}")
        return run_smoke(workdir, model, base)

    with tempfile.TemporaryDirectory(prefix="pipeline_smoke_") as name:
        return run_smoke(Path(name), model, base)

if __name__ == "__main__":
    sys.exit(main())
