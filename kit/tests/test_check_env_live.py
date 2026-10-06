"""check_env: the final result must depend on a real answer from the model."""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_env
from lmstudio_models import LoadedModel

LOADED = [LoadedModel('qwen3-coder', 'qwen3-coder', 'Qwen')]

ANSWER = {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}


class TestLiveTest(unittest.TestCase):
    def quiet(self, func, *args):
        with redirect_stdout(io.StringIO()):
            return func(*args)

    def test_no_generative_models_is_a_failure(self):
        self.assertFalse(self.quiet(check_env.live_test, []))

    def test_model_answer_is_a_success(self):
        with patch.object(check_env, "http_post_json", return_value=ANSWER):
            self.assertTrue(self.quiet(check_env.live_test, LOADED))

    def test_request_error_is_a_failure(self):
        with patch.object(check_env, "http_post_json", side_effect=OSError("refused")):
            self.assertFalse(self.quiet(check_env.live_test, LOADED))

    def test_main_fails_when_the_model_does_not_answer(self):
        with patch.object(check_env, "check_config", return_value=True), \
                patch.object(check_env, "check_lmstudio", return_value=LOADED), \
                patch.object(check_env, "http_post_json", side_effect=OSError("refused")):
            self.assertEqual(self.quiet(check_env.main, []), 1)

    def test_main_succeeds_when_everything_works(self):
        with patch.object(check_env, "check_config", return_value=True), \
                patch.object(check_env, "check_lmstudio", return_value=LOADED), \
                patch.object(check_env, "http_post_json", return_value=ANSWER):
            self.assertEqual(self.quiet(check_env.main, []), 0)


if __name__ == "__main__":
    unittest.main()
