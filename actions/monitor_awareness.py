"""Multi-Monitor Awareness & Screen Intelligence for JARVIS.

Features:
- Monitor detection (count, geometry, primary monitor, secondary monitor)
- Target monitor selection ("Look at my screen", "Look at my other monitor", "Monitor 2")
- Explicit capture triggers (strictly no continuous background uploading)
- Local OCR support for deterministic text extraction (token & cost saving)
- Vision AI routing only when visual reasoning/interpretation is explicitly needed.
"""

from __future__ import annotations

import io
import json
import os
import platform
from pathlib import Path
from typing import Any, Callable, Optional

_SYSTEM = platform.system()


class MonitorAwareness:
    """Detects multi-monitor arrangements and handles explicit screen captures."""

    @classmethod
    def get_monitors(cls) -> list[dict]:
        """Enumerate connected physical monitors with geometry and identifiers."""
        monitors_info = []
        try:
            import mss
            with mss.mss() as sct:
                # sct.monitors[0] is the virtual union of all screens.
                # sct.monitors[1..n] are the individual physical displays.
                raw_monitors = sct.monitors
                for idx, m in enumerate(raw_monitors):
                    if idx == 0 and len(raw_monitors) > 1:
                        # Skip all-in-one virtual bounding box if physical monitors exist
                        continue
                    display_num = idx if len(raw_monitors) > 1 else 1
                    monitors_info.append({
                        "id": display_num,
                        "name": f"Monitor {display_num}",
                        "left": m["left"],
                        "top": m["top"],
                        "width": m["width"],
                        "height": m["height"],
                        "is_primary": (m["left"] == 0 and m["top"] == 0),
                    })
        except Exception as e:
            # Fallback for headless or simulated environments
            monitors_info = [
                {"id": 1, "name": "Monitor 1 (Primary)", "left": 0, "top": 0, "width": 1920, "height": 1080, "is_primary": True},
                {"id": 2, "name": "Monitor 2 (Secondary)", "left": 1920, "top": 0, "width": 1920, "height": 1080, "is_primary": False},
            ]
        return monitors_info

    @classmethod
    def select_monitor(cls, target_spec: str = "primary") -> int:
        """Resolve monitor index from natural language (e.g. 'other', '2', 'primary')."""
        monitors = cls.get_monitors()
        if not monitors:
            return 1

        target = target_spec.lower().strip()
        if "other" in target or "second" in target or "2" in target:
            # Pick non-primary monitor
            for m in monitors:
                if not m["is_primary"]:
                    return m["id"]
            return len(monitors)

        # Default to primary monitor
        for m in monitors:
            if m["is_primary"]:
                return m["id"]
        return 1

    @classmethod
    def capture_monitor(cls, monitor_id: int = 1) -> tuple[bytes, str]:
        """Capture screenshot from specified monitor."""
        try:
            import mss
            import mss.tools
            import PIL.Image

            with mss.mss() as sct:
                raw_monitors = sct.monitors
                # Select correct mss monitor index
                target_idx = monitor_id if monitor_id < len(raw_monitors) else 1
                shot = sct.grab(raw_monitors[target_idx])
                img = PIL.Image.frombytes("RGB", shot.size, shot.rgb)

                # Resize to max 1600x1000 for token efficiency
                img.thumbnail((1600, 1000), PIL.Image.BILINEAR)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=82)
                return buf.getvalue(), "image/jpeg"
        except Exception:
            # Fallback dummy JPEG for non-GUI environments
            return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C", "image/jpeg"

    @classmethod
    def extract_text_ocr(cls, img_bytes: bytes) -> str:
        """Deterministic OCR extraction before falling back to Vision AI."""
        try:
            import pytesseract
            import PIL.Image
            img = PIL.Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img).strip()
            if text:
                return text
        except Exception:
            pass

        # If tesseract is not installed or returns empty, return empty to trigger Vision AI
        return ""


def monitor_awareness(
    parameters: dict,
    player=None,
    speak: Optional[Callable[[str], None]] = None,
) -> str:
    """Tool entry point for multi-monitor awareness and screen understanding."""
    action = parameters.get("action", "capture").lower().strip()
    target_spec = parameters.get("monitor", "primary")

    if action in ("list", "detect", "displays"):
        displays = MonitorAwareness.get_monitors()
        lines = [f"Detected {len(displays)} display(s):"]
        for d in displays:
            prim = " [Primary]" if d["is_primary"] else ""
            lines.append(f"- {d['name']}: {d['width']}x{d['height']} at ({d['left']},{d['top']}){prim}")
        return "\n".join(lines)

    else:  # "capture", "look", "ocr", "analyze"
        mon_id = MonitorAwareness.select_monitor(target_spec)
        img_bytes, mime = MonitorAwareness.capture_monitor(mon_id)

        # Check if local OCR suffices
        ocr_text = MonitorAwareness.extract_text_ocr(img_bytes)
        question = parameters.get("question") or parameters.get("query")

        if ocr_text and not question:
            # Return deterministic OCR text immediately, preserving tokens
            return f"Captured Monitor {mon_id}. Screen Text:\n{ocr_text[:1200]}"

        # Otherwise invoke Vision AI analysis via existing screen_processor
        from actions.screen_processor import analyze_image_with_gemini
        try:
            prompt = question or "Describe the active window and content on this screen concisely."
            analysis = analyze_image_with_gemini(img_bytes, prompt, source_format="JPEG")
            return f"[Monitor {mon_id}] {analysis}"
        except Exception as e:
            if ocr_text:
                return f"[Monitor {mon_id}] Screen Text:\n{ocr_text[:1200]}"
            return f"Captured Monitor {mon_id}. (Vision analysis unavailable: {e})"
