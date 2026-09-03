import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from actions.word_intelligence import WordDocumentIntelligence, word_intelligence
from actions.file_search import FileIntelligence, file_intelligence
from actions.monitor_awareness import MonitorAwareness, monitor_awareness
from actions.study_tutor import StudyTutor, study_tutor
from actions.memory_tool import memory_control
from core.provider_manager import ProviderManager, provider_control
from actions.background_runner import BackgroundRunner, background_control
from agent.executor import _call_tool


class CapabilitiesTestSuite(unittest.TestCase):

    # 1. Word Intelligence
    def test_word_intelligence_destructive_confirmation(self):
        # Section 12 check: confirmation required before replacing
        res = word_intelligence({"action": "replace", "heading": "Intro", "text": "New text", "confirmed": False})
        self.assertIn("SAFETY CONFIRMATION REQUIRED", res)

        # When confirmed, it proceeds
        with patch.object(WordDocumentIntelligence, "is_windows", return_value=False):
            res_conf = word_intelligence({"action": "replace", "heading": "Intro", "text": "New text", "confirmed": True})
            self.assertIn("Confirmed", res_conf)

    def test_word_intelligence_outline(self):
        res = word_intelligence({"action": "outline"})
        self.assertIn("Document", res)
        self.assertIn("paragraphs", res)

    # 2. File Intelligence
    def test_file_intelligence_blocked_secrets(self):
        secret_env = Path.home() / "Documents" / ".env"
        self.assertFalse(FileIntelligence.is_path_authorized(secret_env))

        safe_doc = Path.home() / "Documents" / "project_report.docx"
        # Since Documents is in default authorized roots
        self.assertTrue(FileIntelligence.is_path_authorized(safe_doc))

    def test_file_intelligence_read_excerpt_truncation(self):
        # Test that large text extracts do not bloat context window
        test_file = Path(__file__).resolve()
        res = FileIntelligence.read_document_excerpt(str(test_file), max_chars=100)
        self.assertTrue(res.get("ok"))
        self.assertIn("truncated", res.get("excerpt", ""))

    # 3. Monitor Awareness
    def test_monitor_detection_and_selection(self):
        monitors = MonitorAwareness.get_monitors()
        self.assertGreaterEqual(len(monitors), 1)

        prim_id = MonitorAwareness.select_monitor("primary")
        self.assertEqual(prim_id, 1)

        other_id = MonitorAwareness.select_monitor("other")
        self.assertIn(other_id, [m["id"] for m in monitors])

    # 4. Study / Tutor
    def test_study_tutor_basic(self):
        res = study_tutor({"topic": "Newton's Second Law", "mode": "guide"})
        self.assertTrue(len(res) > 10)

    # 5. Memory Tool & Truthful Recall (Section 20)
    def test_memory_no_hallucination_on_missing(self):
        # If memory not found, MUST NOT pretend to remember
        res = memory_control({"action": "search", "query": "non_existent_super_secret_query_xyz_999"})
        self.assertIn("could not find", res.lower())
        self.assertIn("provide me with that information again", res.lower())

    def test_memory_store_and_forget(self):
        save_res = memory_control({"action": "store", "key": "favorite_coffee", "value": "flat white", "category": "preferences"})
        self.assertIn("Remembered", save_res)

        search_res = memory_control({"action": "search", "query": "coffee"})
        self.assertIn("flat white", search_res)

        forget_res = memory_control({"action": "forget", "key": "favorite_coffee", "category": "preferences"})
        self.assertIn("Forgotten", forget_res)

    # 6. AI Provider Manager (Section 6 & 7: No silent automatic fallback)
    def test_provider_manager_manual_switch(self):
        # List providers
        providers = ProviderManager.list_providers()
        p_ids = [p["id"] for p in providers]
        self.assertIn("gemini", p_ids)
        self.assertIn("ollama", p_ids)
        self.assertIn("claude", p_ids)
        self.assertIn("openai", p_ids)

        # Switch manually to Ollama
        ok, msg = ProviderManager.set_active_provider("ollama")
        self.assertTrue(ok)
        self.assertEqual(ProviderManager.get_active_provider(), "ollama")

        # Switch back to gemini
        ok, msg = ProviderManager.set_active_provider("gemini")
        self.assertTrue(ok)
        self.assertEqual(ProviderManager.get_active_provider(), "gemini")

    # 7. Background Control
    def test_background_runner(self):
        res = background_control({"action": "minimize"})
        self.assertTrue(BackgroundRunner.is_minimized())
        self.assertIn("background", res.lower())

        res_fg = background_control({"action": "restore"})
        self.assertFalse(BackgroundRunner.is_minimized())

    # 8. Executor Tool Dispatching
    def test_executor_dispatches_new_tools(self):
        res1 = _call_tool("word_intelligence", {"action": "outline"}, speak=None)
        self.assertIn("Document", res1)

        res2 = _call_tool("provider_control", {"action": "status"}, speak=None)
        self.assertIn("Active Provider", res2)

        res3 = _call_tool("background_control", {"action": "status"}, speak=None)
        self.assertIn("JARVIS Execution State", res3)


if __name__ == "__main__":
    unittest.main()
