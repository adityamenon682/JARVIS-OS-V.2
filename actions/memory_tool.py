"""User Memory Tool for JARVIS.

Enables user-controlled, searchable, editable, and deletable long-term memory:
- Explicit search without dumping entire memory into prompts
- Strict rule: if information cannot be found, never pretend or hallucinate;
  inform the user clearly and request the information again.
- Category management: preferences, projects, relationships, wishes, notes.
"""

from __future__ import annotations

from typing import Callable, Optional
from memory.memory_manager import load_memory, remember, forget, search_memory


def memory_control(
    parameters: dict,
    player=None,
    speak: Optional[Callable[[str], None]] = None,
) -> str:
    """Tool entry point for searching and managing user memories."""
    action = parameters.get("action", "search").lower().strip()
    query = parameters.get("query") or parameters.get("text") or ""
    key = parameters.get("key", "").strip()
    value = parameters.get("value", "").strip()
    category = parameters.get("category", "notes").strip().lower()

    if action in ("store", "remember", "save"):
        if not key or not value:
            return "Please provide both a key and value to remember."
        res = remember(key, value, category=category)
        if speak:
            speak(f"I will remember that, sir.")
        return res

    elif action in ("forget", "delete", "remove"):
        if not key:
            return "Please provide the key to forget."
        res = forget(key, category=category)
        if speak:
            speak(f"Removed from memory.")
        return res

    elif action in ("list", "all"):
        mem = load_memory()
        lines = ["Current memory overview:"]
        for cat, items in mem.items():
            if items:
                lines.append(f"[{cat.upper()}]: {len(items)} item(s)")
        return "\n".join(lines)

    else:  # "search", "recall", "find"
        if not query:
            return "Please provide what you would like me to recall."

        matches = search_memory(query)
        if not matches:
            # Mandated by Section 20: DO NOT pretend to remember it.
            msg = f"I could not find any saved memories regarding '{query}'. Could you please remind or provide me with that information again?"
            if speak:
                speak(msg)
            return msg

        lines = [f"Found {len(matches)} relevant memory item(s):"]
        for m in matches[:5]:
            lines.append(f"- [{m['category']}] {m['key']}: {m['value']}")
        return "\n".join(lines)
