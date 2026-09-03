"""Study & Tutoring System for JARVIS.

Designed for active learning, homework assistance, concept explanation,
and step-by-step tutoring.
Adheres strictly to Section 22:
- Guides step-by-step rather than immediately giving the final answer when learning
- Explains concepts with clarity and relatable examples
- Verifies understanding and checks for mistakes
- Adapts explanations to user's knowledge level.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional


class StudyTutor:
    """Provides step-by-step tutoring and homework guidance."""

    @classmethod
    def get_api_key(cls) -> str:
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_key:
            return env_key
        try:
            import json
            p = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("gemini_api_key") or data.get("GEMINI_API_KEY") or ""
        except Exception:
            pass
        return ""

    @classmethod
    def tutor_session(
        cls,
        question_or_topic: str,
        user_attempt: Optional[str] = None,
        mode: str = "guide",  # "guide" | "explain" | "quiz" | "check"
    ) -> str:
        api_key = cls.get_api_key()
        if not api_key:
            return (
                f"Tutoring guidance for: {question_or_topic}\n\n"
                f"1. Break down the core principles involved.\n"
                f"2. Identify the known variables and target outcome.\n"
                f"3. Work through the first logical step before jumping to conclusions."
            )

        system_instruction = (
            "You are JARVIS in Tutor Mode. Your goal is to help the student learn deeply. "
            "Rule #1: When guiding or solving a problem, do NOT immediately blurt out the final answer. "
            "Break down the concept into intuitive, step-by-step explanations. "
            "Ask an engaging question or check their understanding of the first step. "
            "If the student provided an attempt, highlight what they did well and kindly point out where the misconception lies. "
            "Keep the tone encouraging, concise, and structured like a world-class mentor."
        )

        user_prompt = f"Topic / Question: {question_or_topic}\n"
        if user_attempt:
            user_prompt += f"My Attempt / Thoughts: {user_attempt}\n"
        user_prompt += f"Tutoring Mode: {mode}"

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config={"system_instruction": system_instruction}
            )
            return resp.text.strip()
        except Exception:
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=api_key)
                model = legacy_genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=system_instruction
                )
                resp = model.generate_content(user_prompt)
                return resp.text.strip()
            except Exception as e:
                return f"Tutoring assistant encountered an error: {e}"


def study_tutor(
    parameters: dict,
    player=None,
    speak: Optional[Callable[[str], None]] = None,
) -> str:
    """Tool entry point for study and tutoring."""
    topic = parameters.get("topic") or parameters.get("question") or ""
    attempt = parameters.get("attempt") or parameters.get("user_answer") or ""
    mode = parameters.get("mode", "guide")

    if not topic:
        return "Please specify the topic or question you would like to study."

    if speak:
        speak("Let's break down this problem together, sir.")

    return StudyTutor.tutor_session(topic, user_attempt=attempt, mode=mode)
