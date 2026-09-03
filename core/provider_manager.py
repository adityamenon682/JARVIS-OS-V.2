"""AI Provider Manager for JARVIS.

Manages manually selectable AI providers with a strict Free-First philosophy:
- Providers: Gemini, Claude, OpenAI/Copilot, Local/Ollama
- CRITICAL: NO AUTOMATIC FALLBACK SYSTEM. Never silently switch models.
  If the active provider hits rate limits or becomes unavailable, report the error
  truthfully to the user and prompt them to switch manually if they wish.
- Exposes available quota / usage details only when truthfully provided by the API.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "provider_settings.json"


@dataclass
class ProviderInfo:
    id: str
    name: str
    is_active: bool
    is_local: bool
    description: str
    model_name: str
    base_url: Optional[str] = None
    usage_info: Optional[str] = None


class ProviderManager:
    """Central registry and controller for manual AI provider selection."""

    AVAILABLE_PROVIDERS = {
        "gemini": {
            "name": "Google Gemini",
            "is_local": False,
            "description": "Primary multimodal model (Gemini 2.5 Flash, free tier supported)",
            "default_model": "gemini-2.5-flash",
        },
        "ollama": {
            "name": "Local Ollama / Open-Source",
            "is_local": True,
            "description": "100% Free local offline model (e.g. Llama 3, Mistral, Qwen)",
            "default_model": "llama3:latest",
            "base_url": "http://localhost:11434",
        },
        "claude": {
            "name": "Anthropic Claude",
            "is_local": False,
            "description": "Claude 3.5 Sonnet / Haiku (requires Anthropic API key)",
            "default_model": "claude-3-5-sonnet-20241022",
        },
        "openai": {
            "name": "OpenAI / Copilot",
            "is_local": False,
            "description": "GPT-4o / Copilot endpoint (requires OpenAI key)",
            "default_model": "gpt-4o",
        },
    }

    @classmethod
    def load_settings(cls) -> dict:
        if _CONFIG_PATH.exists():
            try:
                return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "active_provider": "gemini",
            "model_overrides": {},
            "provider_keys": {},
        }

    @classmethod
    def save_settings(cls, settings: dict) -> None:
        try:
            _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CONFIG_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ProviderManager] ⚠️ Error saving provider settings: {e}")

    @classmethod
    def get_active_provider(cls) -> str:
        settings = cls.load_settings()
        return settings.get("active_provider", "gemini")

    @classmethod
    def set_active_provider(cls, provider_id: str) -> tuple[bool, str]:
        """Manually switch active AI provider.

        Strictly manual — automatic silent switching is forbidden by design.
        """
        pid = provider_id.lower().strip()
        if pid not in cls.AVAILABLE_PROVIDERS:
            return False, f"Unknown provider '{provider_id}'. Available: {list(cls.AVAILABLE_PROVIDERS.keys())}"

        settings = cls.load_settings()
        settings["active_provider"] = pid
        cls.save_settings(settings)
        name = cls.AVAILABLE_PROVIDERS[pid]["name"]
        return True, f"Active AI provider manually switched to {name}."

    @classmethod
    def list_providers(cls) -> list[dict]:
        settings = cls.load_settings()
        active_id = settings.get("active_provider", "gemini")
        result = []
        for pid, pdata in cls.AVAILABLE_PROVIDERS.items():
            result.append({
                "id": pid,
                "name": pdata["name"],
                "is_active": (pid == active_id),
                "is_local": pdata["is_local"],
                "description": pdata["description"],
                "model_name": settings.get("model_overrides", {}).get(pid, pdata["default_model"]),
            })
        return result

    @classmethod
    def get_provider_status(cls) -> str:
        settings = cls.load_settings()
        active_id = settings.get("active_provider", "gemini")
        pdata = cls.AVAILABLE_PROVIDERS.get(active_id, cls.AVAILABLE_PROVIDERS["gemini"])

        status_str = f"Active Provider: {pdata['name']} (Model: {pdata['default_model']})"
        if pdata["is_local"]:
            status_str += " [Local/Free Offline Mode]"
        else:
            status_str += " [Cloud Provider - Subject to user quota]"
        return status_str


def provider_control(
    parameters: dict,
    player=None,
    speak: Optional[Callable[[str], None]] = None,
) -> str:
    """Tool entry point for inspecting and manually selecting AI providers."""
    action = parameters.get("action", "status").lower().strip()
    provider_id = parameters.get("provider") or parameters.get("name") or ""

    if action in ("select", "set", "switch", "change"):
        if not provider_id:
            return "Please specify which provider to switch to (gemini, ollama, claude, openai)."
        ok, msg = ProviderManager.set_active_provider(provider_id)
        if speak:
            speak(msg)
        return msg

    elif action in ("list", "all"):
        providers = ProviderManager.list_providers()
        lines = ["Configured AI Providers:"]
        for p in providers:
            active_flag = " [*ACTIVE*]" if p["is_active"] else ""
            local_flag = " (100% Local/Free)" if p["is_local"] else " (Cloud)"
            lines.append(f"- {p['id']}: {p['name']}{local_flag}{active_flag} — {p['description']}")
        lines.append("\nNote: Per Master Instruction, automatic silent model switching is disabled.")
        return "\n".join(lines)

    else:  # "status"
        return ProviderManager.get_provider_status()
