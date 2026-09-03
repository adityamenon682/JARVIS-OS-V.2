import unittest
from unittest.mock import MagicMock, patch

from actions.word_typing import (
    SPEED_PROFILES,
    WindowsWordController,
    refine_text_with_ai,
    type_text_humanlike,
    word_typing,
)
from agent.executor import _call_tool


class WordTypingTests(unittest.TestCase):
    def test_speed_profiles_defined(self):
        self.assertIn("human", SPEED_PROFILES)
        self.assertIn("normal", SPEED_PROFILES)
        self.assertIn("slow", SPEED_PROFILES)
        self.assertIn("fast", SPEED_PROFILES)
        self.assertIn("very_fast", SPEED_PROFILES)
        self.assertIn("instant", SPEED_PROFILES)

        # Ensure human profile has positive keystroke jitter and pause times
        base_min, base_max, space_p, punct_p, nl_p = SPEED_PROFILES["human"]
        self.assertGreater(base_min, 0)
        self.assertGreater(base_max, base_min)
        self.assertGreater(punct_p, 0)

        # Instant has 0 delay
        self.assertEqual(SPEED_PROFILES["instant"], (0.0, 0.0, 0.0, 0.0, 0.0))

    def test_type_text_humanlike_counts_characters(self):
        text = "Hello, Word!\nThis is JARVIS typing."
        typed = type_text_humanlike(text, speed="instant")
        self.assertEqual(typed, len(text))

    def test_safety_check_halts_on_focus_loss(self):
        text = "This is a long sentence that should stop if Word loses focus."
        # Safety check returns True for first 10 chars, then False (simulating focus loss)
        call_count = {"val": 0}

        def fake_safety():
            call_count["val"] += 1
            return call_count["val"] <= 10

        typed = type_text_humanlike(text, speed="instant", safety_check=fake_safety)
        self.assertEqual(typed, 10)
        self.assertLess(typed, len(text))

    def test_word_not_open_returns_specified_message(self):
        with patch.object(WindowsWordController, "is_windows", return_value=True), \
             patch.object(WindowsWordController, "get_word_windows", return_value=[]), \
             patch.object(WindowsWordController, "open_or_launch_word", return_value=False):
            res = word_typing({"text": "Hello document"})
            self.assertEqual(res, "Microsoft Word isn't open and I couldn't locate the document.")

    def test_word_typing_empty_text(self):
        res = word_typing({"text": ""})
        self.assertEqual(res, "No text provided to write into Microsoft Word.")

    def test_word_typing_simulated_success(self):
        res = word_typing({"text": "Hello world", "speed": "fast"}, mock=True)
        self.assertIn("Successfully typed 11 characters into Microsoft Word", res)

    def test_executor_tool_dispatch(self):
        with patch("actions.word_typing.word_typing", return_value="Typed 42 characters."):
            res = _call_tool("word_typing", {"text": "Test text"}, speak=None)
            self.assertEqual(res, "Typed 42 characters.")

            res_alias = _call_tool("type_into_word", {"text": "Test text"}, speak=None)
            self.assertEqual(res_alias, "Typed 42 characters.")

    def test_refine_text_verbatim_leaves_unchanged(self):
        raw = "This is my unedited thought."
        result = refine_text_with_ai(raw, mode="verbatim")
        self.assertEqual(result, raw)


if __name__ == "__main__":
    unittest.main()
