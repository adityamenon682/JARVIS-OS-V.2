import os
from typing import Any, Dict, Optional

class JarvisClient:
    """Client for JARVIS agent runtime and backend integration."""
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("JARVIS_API_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("JARVIS_API_KEY", "")

    def is_connected(self) -> bool:
        return False

    def emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        pass
