import os

def pick_live_model() -> str:
    """Select the Gemini Live audio/multimodal model."""
    return os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash")
