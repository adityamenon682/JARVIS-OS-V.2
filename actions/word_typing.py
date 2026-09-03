"""Human-like Microsoft Word Typing Action for JARVIS.

Enables JARVIS to type text into Microsoft Word through authentic Windows
keyboard and input automation rather than clipboard pasting.
Supports natural human rhythm with keystroke jitter and punctuation pauses,
configurable speeds, window focus safety checks, document placement,
and optional thought-to-writing refinement.
"""

from __future__ import annotations

import os
import platform
import random
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

_SYSTEM = platform.system()

# Speed delay profiles: (base_min, base_max, space_pause, punct_pause, newline_pause) in seconds
SPEED_PROFILES = {
    "human": (0.045, 0.075, 0.025, 0.180, 0.280),
    "normal": (0.045, 0.075, 0.025, 0.180, 0.280),
    "slow": (0.110, 0.180, 0.050, 0.300, 0.450),
    "fast": (0.015, 0.030, 0.008, 0.040, 0.080),
    "very_fast": (0.005, 0.012, 0.002, 0.015, 0.030),
    "instant": (0.000, 0.000, 0.000, 0.000, 0.000),
}


@dataclass
class WordTypingResult:
    ok: bool
    message: str
    typed_characters: int = 0
    speed: str = "human"
    document_title: str = ""
    refined: bool = False


def _get_api_key() -> str:
    """Retrieve Gemini API key for text refinement if requested."""
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        import json
        config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("gemini_api_key") or data.get("GEMINI_API_KEY") or ""
    except Exception:
        pass
    return ""


def refine_text_with_ai(text: str, instruction: str = "", mode: str = "verbatim") -> str:
    """Refine user thoughts into structured document-ready writing while preserving meaning."""
    if not text:
        return ""
    if mode == "verbatim" and not instruction:
        return text

    api_key = _get_api_key()
    if not api_key:
        return text

    system_instruction = (
        "You are JARVIS's writing assistant. Take the user's raw thought or draft and refine it for Microsoft Word. "
        "Preserve the core meaning, facts, and intent. Do NOT add fictional details. "
        "Output ONLY the refined text to be typed into the document. Do not add conversational chatter or quotes."
    )

    style_guide = ""
    if mode == "formal":
        style_guide = "Use professional, academic, or formal business tone."
    elif mode == "clear":
        style_guide = "Improve clarity, grammar, and flow while keeping the author's natural voice."
    elif mode == "summarize":
        style_guide = "Summarize the key points concisely in well-structured paragraphs."
    elif instruction:
        style_guide = f"Follow this specific instruction: {instruction}"

    prompt = f"{style_guide}\n\nOriginal draft:\n{text}"

    try:
        # Try modern google.genai or legacy google.generativeai
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"system_instruction": system_instruction}
            )
            refined = response.text.strip()
            if refined:
                return refined
        except ImportError:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=api_key)
            model = legacy_genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            refined = response.text.strip()
            if refined:
                return refined
    except Exception as exc:
        print(f"[WordTyping] ⚠️ Text refinement skipped: {exc}")

    return text


class WindowsWordController:
    """Manages Microsoft Word window detection, focus, and input automation on Windows."""

    @staticmethod
    def is_windows() -> bool:
        return _SYSTEM == "Windows"

    @classmethod
    def get_word_windows(cls) -> list[dict]:
        """Enumerate active Microsoft Word windows."""
        if not cls.is_windows():
            return []

        word_windows = []

        # Try win32gui / ctypes window enumeration
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            def enum_windows_callback(hwnd, extra):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value

                        class_buff = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(hwnd, class_buff, 256)
                        class_name = class_buff.value

                        # Microsoft Word window class is 'OpusApp'
                        if class_name == "OpusApp" or " - Word" in title or title.endswith("Word"):
                            word_windows.append({
                                "hwnd": hwnd,
                                "title": title,
                                "class_name": class_name,
                            })
                return True

            EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        except Exception as e:
            print(f"[WordTyping] Error enumerating windows via ctypes: {e}")

        # Fallback to pygetwindow if ctypes enumeration found nothing
        if not word_windows:
            try:
                import pygetwindow as gw
                for win in gw.getAllWindows():
                    if win.visible and ("Word" in win.title or win.title.endswith(".docx")):
                        word_windows.append({
                            "hwnd": getattr(win, "_hWnd", 0),
                            "title": win.title,
                            "class_name": "OpusApp",
                        })
            except Exception:
                pass

        return word_windows

    @classmethod
    def get_foreground_window_info(cls) -> dict:
        """Returns HWND, title, and class name of the current foreground window."""
        if not cls.is_windows():
            return {"hwnd": 0, "title": "", "class_name": ""}

        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return {"hwnd": 0, "title": "", "class_name": ""}

            length = user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value

            class_buff = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buff, 256)
            class_name = class_buff.value

            return {"hwnd": hwnd, "title": title, "class_name": class_name}
        except Exception:
            return {"hwnd": 0, "title": "", "class_name": ""}

    @classmethod
    def is_word_foreground(cls) -> bool:
        """Verify that Microsoft Word is the active, focused foreground window."""
        info = cls.get_foreground_window_info()
        return (
            info.get("class_name") == "OpusApp"
            or " - Word" in info.get("title", "")
            or info.get("title", "").endswith("Word")
        )

    @classmethod
    def focus_word_window(cls, hwnd: int) -> bool:
        """Bring the specified Word window to the foreground."""
        if not cls.is_windows() or not hwnd:
            return False

        try:
            import ctypes
            user32 = ctypes.windll.user32

            # If minimized, restore it (SW_RESTORE = 9)
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)

            user32.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            return cls.is_word_foreground()
        except Exception as e:
            print(f"[WordTyping] Failed to focus window: {e}")
            return False

    @classmethod
    def open_or_launch_word(cls, doc_path: Optional[str] = None) -> bool:
        """Launch Microsoft Word or open a specific document."""
        try:
            if doc_path and Path(doc_path).exists():
                if cls.is_windows():
                    os.startfile(str(doc_path))
                else:
                    subprocess.Popen(["open" if _SYSTEM == "Darwin" else "xdg-open", str(doc_path)])
            else:
                if cls.is_windows():
                    subprocess.Popen(["start", "winword"], shell=True)
                else:
                    subprocess.Popen(["libreoffice", "--writer"])
            time.sleep(2.0)
            return True
        except Exception as e:
            print(f"[WordTyping] Failed to launch Word: {e}")
            return False

    @classmethod
    def position_cursor(cls, placement: str = "cursor") -> None:
        """Adjust cursor placement in Word before typing."""
        if placement == "cursor":
            return

        # Attempt placement via COM if available
        try:
            import win32com.client
            word_app = win32com.client.GetActiveObject("Word.Application")
            if word_app and word_app.Selection:
                if placement == "end":
                    word_app.Selection.EndKey(Unit=6)  # wdStory = 6
                    return
                elif placement == "beginning":
                    word_app.Selection.HomeKey(Unit=6)
                    return
                elif placement == "new_paragraph":
                    word_app.Selection.EndKey(Unit=6)
                    word_app.Selection.TypeParagraph()
                    return
        except Exception:
            pass

        # Fallback to standard Windows shortcut keys
        try:
            import pyautogui
            if placement == "end":
                pyautogui.hotkey("ctrl", "end")
            elif placement == "beginning":
                pyautogui.hotkey("ctrl", "home")
            elif placement == "new_paragraph":
                pyautogui.hotkey("ctrl", "end")
                pyautogui.press("enter")
            time.sleep(0.1)
        except Exception:
            pass


def send_unicode_char_windows(char: str) -> bool:
    """Send a single Unicode character using the Windows SendInput API."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002
    INPUT_KEYBOARD = 1

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_ulong),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", wintypes.DWORD),
            ("union", INPUT_UNION),
        ]

    code = ord(char)

    # Press
    inp_down = INPUT()
    inp_down.type = INPUT_KEYBOARD
    inp_down.union.ki.wVk = 0
    inp_down.union.ki.wScan = code
    inp_down.union.ki.dwFlags = KEYEVENTF_UNICODE
    inp_down.union.ki.time = 0
    inp_down.union.ki.dwExtraInfo = 0

    # Release
    inp_up = INPUT()
    inp_up.type = INPUT_KEYBOARD
    inp_up.union.ki.wVk = 0
    inp_up.union.ki.wScan = code
    inp_up.union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    inp_up.union.ki.time = 0
    inp_up.union.ki.dwExtraInfo = 0

    inputs = (INPUT * 2)(inp_down, inp_up)
    res = user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    return res > 0


def type_text_humanlike(
    text: str,
    speed: str = "human",
    safety_check: Optional[Callable[[], bool]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> int:
    """Type text with realistic human rhythm and safety checks.

    NOT a clipboard paste. Sends each character via keyboard input automation.
    """
    profile = SPEED_PROFILES.get(speed.lower(), SPEED_PROFILES["human"])
    base_min, base_max, space_pause, punct_pause, newline_pause = profile

    is_windows = WindowsWordController.is_windows()
    typed_count = 0
    total_len = len(text)

    # Use pyautogui fallback if not on Windows
    pyautogui_module = None
    if not is_windows:
        try:
            import pyautogui
            pyautogui_module = pyautogui
        except ImportError:
            pass

    for i, char in enumerate(text):
        # Continuous Safety check: ensure Word hasn't lost focus
        if safety_check and not safety_check():
            print(f"[WordTyping] ⚠️ Word lost focus at character {i}/{total_len}. Halting typing for safety.")
            break

        # Handle Enter / newline
        if char == "\n":
            if is_windows:
                send_unicode_char_windows("\r")
            elif pyautogui_module:
                pyautogui_module.press("enter")
            if newline_pause > 0:
                time.sleep(newline_pause + random.uniform(0.01, 0.05))
            typed_count += 1
            if on_progress:
                on_progress(typed_count, total_len)
            continue

        # Handle Tab
        if char == "\t":
            if is_windows:
                send_unicode_char_windows("\t")
            elif pyautogui_module:
                pyautogui_module.press("tab")
            if base_max > 0:
                time.sleep(random.uniform(base_min, base_max))
            typed_count += 1
            if on_progress:
                on_progress(typed_count, total_len)
            continue

        # Keystroke typing
        if is_windows:
            success = send_unicode_char_windows(char)
            if not success and pyautogui_module:
                pyautogui_module.write(char)
        elif pyautogui_module:
            pyautogui_module.write(char)
        else:
            # Simulated environment (e.g. testing container)
            pass

        typed_count += 1

        if on_progress and (typed_count % 10 == 0 or typed_count == total_len):
            on_progress(typed_count, total_len)

        # Apply human rhythm pauses
        if base_max > 0:
            # Baseline keystroke jitter
            jitter = random.uniform(base_min, base_max)
            time.sleep(jitter)

            # Extra pause after space (word boundary reflection)
            if char == " " and space_pause > 0:
                time.sleep(random.uniform(0.005, space_pause))

            # Extra pause after punctuation marks
            elif char in ".!?" and punct_pause > 0:
                time.sleep(random.uniform(punct_pause * 0.7, punct_pause * 1.3))
            elif char in ",;:" and punct_pause > 0:
                time.sleep(random.uniform(punct_pause * 0.4, punct_pause * 0.7))

    return typed_count


def word_typing(
    parameters: dict,
    player=None,
    speak: Optional[Callable[[str], None]] = None,
    mock: bool = False,
) -> str:
    """Execute human-like Microsoft Word typing.

    Parameters:
      text: string (required) - text or writing to type into Word
      document_name: string (optional) - specific Word document name/title
      document_path: string (optional) - file path to .docx
      speed: "human" | "normal" | "slow" | "fast" | "very_fast" | "instant" (default: human)
      mode: "verbatim" | "polish" | "formal" | "clear" | "summarize" (default: verbatim)
      placement: "cursor" | "end" | "beginning" | "new_paragraph" (default: cursor)
      instruction: string (optional) - natural language instruction for restructuring
    """
    raw_text = parameters.get("text") or parameters.get("content") or ""
    if not raw_text:
        return "No text provided to write into Microsoft Word."

    doc_name = parameters.get("document_name", "").strip()
    doc_path = parameters.get("document_path", "").strip()
    speed = str(parameters.get("speed", "human")).lower().strip()
    if speed not in SPEED_PROFILES:
        speed = "human"

    mode = str(parameters.get("mode", "verbatim")).lower().strip()
    placement = str(parameters.get("placement", "cursor")).lower().strip()
    instruction = str(parameters.get("instruction", "")).strip()

    # Step 1: Optional AI thought restructuring
    text_to_type = raw_text
    refined = False
    if instruction or mode != "verbatim":
        if speak:
            speak("Refining your text for the Word document, sir.")
        text_to_type = refine_text_with_ai(raw_text, instruction=instruction, mode=mode)
        refined = (text_to_type != raw_text)

    # In mock or testing mode on non-Windows environments
    if mock or not WindowsWordController.is_windows():
        typed = type_text_humanlike(text_to_type, speed="instant")
        if speak:
            speak(f"Finished typing {typed} characters into Microsoft Word.")
        return (
            f"Successfully typed {typed} characters into Microsoft Word at '{speed}' speed "
            f"(simulated environment, placement='{placement}')."
        )

    # Step 2: Locate Microsoft Word window
    word_windows = WindowsWordController.get_word_windows()
    target_window = None

    if word_windows:
        if doc_name:
            # Find window matching document_name
            for win in word_windows:
                if doc_name.lower() in win["title"].lower():
                    target_window = win
                    break
        if not target_window:
            # Default to the primary active Word window
            target_window = word_windows[0]
    else:
        # Word is not open — try launching it or opening the document path
        opened = WindowsWordController.open_or_launch_word(doc_path)
        if opened:
            time.sleep(2.0)
            word_windows = WindowsWordController.get_word_windows()
            if word_windows:
                target_window = word_windows[0]

    # If Word still cannot be found, report clearly per Section 31
    if not target_window:
        msg = "Microsoft Word isn't open and I couldn't locate the document."
        if speak:
            speak(msg)
        return msg

    # Step 3: Ensure Word is focused and in foreground
    focused = WindowsWordController.focus_word_window(target_window["hwnd"])
    if not focused:
        # Double check if foreground is Word
        if not WindowsWordController.is_word_foreground():
            msg = f"Could not safely focus Microsoft Word window ('{target_window['title']}'). Aborted typing for safety."
            if speak:
                speak(msg)
            return msg

    # Step 4: Position insertion point
    WindowsWordController.position_cursor(placement)

    if speak:
        speak(f"Typing into Word at {speed} speed, sir.")

    # Step 5: Type content through Windows keyboard/input automation
    # Continuous safety check verifies the active foreground window remains Word
    safety_check = WindowsWordController.is_word_foreground

    typed_characters = type_text_humanlike(
        text_to_type,
        speed=speed,
        safety_check=safety_check,
    )

    result_summary = (
        f"Successfully typed {typed_characters} characters into Microsoft Word "
        f"('{target_window['title']}') at '{speed}' speed."
    )
    if refined:
        result_summary += " Text was refined per your instructions before typing."

    return result_summary
