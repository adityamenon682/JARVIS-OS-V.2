"""Shared Gemini Live model selection for startup audio and active JARVIS."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


DEFAULT_LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
LIVE_ACTION = "bidiGenerateContent"


def configured_live_model(config_path: Optional[Path] = None) -> str:
    env_model = os.environ.get("GEMINI_LIVE_MODEL", "").strip()
    if env_model:
        return env_model
    if config_path:
        try:
            p = Path(config_path)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                configured = str(data.get("live_model", "") or "").strip()
                if configured:
                    return configured
        except Exception:
            pass
    return DEFAULT_LIVE_MODEL


def _model_name(model: Any) -> str:
    return str(getattr(model, "name", "") or "").strip()


def _model_actions(model: Any) -> set[str]:
    actions = getattr(model, "supported_actions", None)
    if actions is None:
        actions = getattr(model, "supportedActions", None)
    return {str(action).lower() for action in (actions or [])}


def pick_live_model(client: Any = None, config_path: Optional[Path] = None, *args, **kwargs) -> str:
    configured = configured_live_model(config_path)
    if client is None:
        return configured

    try:
        models = list(client.models.list())
    except Exception as exc:
        print(f"[JARVIS] Using configured live_model={configured} (fallback: {exc})")
        return configured

    live_models = [
        _model_name(model)
        for model in models
        if LIVE_ACTION.lower() in _model_actions(model) and _model_name(model)
    ]
    if not live_models:
        return configured

    if configured in live_models:
        return configured

    def score(name: str) -> tuple[int, str]:
        lowered = name.lower()
        if "native-audio" in lowered:
            return (0, name)
        if "live" in lowered:
            return (1, name)
        if "flash" in lowered:
            return (2, name)
        return (3, name)

    selected = sorted(live_models, key=score)[0]
    print(f"[JARVIS] Auto-selected Live model: {selected}")
    return selected
