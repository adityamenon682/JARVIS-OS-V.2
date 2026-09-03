"""File Intelligence & Authorized Folder Search for JARVIS.

Enables secure, permission-respecting file search and document intelligence:
- Authorized folder boundaries (Desktop, Documents, Downloads, user-defined paths)
- Local deterministic search before any AI involvement (token-free file discovery)
- Targeted document extraction (.docx, .pdf, .txt, .md, .py, code)
- Snippet & relevant excerpt extraction to prevent context window bloating
- Strict security: secret files (.env, credentials) blocked from automated ingestion.
"""

from __future__ import annotations

import json
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

_SYSTEM = platform.system()


def _get_default_authorized_roots() -> list[Path]:
    roots = []
    home = Path.home()
    roots.append(home / "Documents")
    roots.append(home / "Desktop")
    roots.append(home / "Downloads")
    # Also add current workspace/project directory
    try:
        roots.append(Path.cwd().resolve())
    except Exception:
        pass
    # Create or return authorized roots
    valid_roots = []
    for r in roots:
        if not r.exists():
            try:
                r.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        valid_roots.append(r)
    return valid_roots


_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_PERMISSIONS_FILE = _CONFIG_DIR / "file_permissions.json"

BLOCKED_PATTERNS = [
    re.compile(r"\.env($|\..*)", re.IGNORECASE),
    re.compile(r"id_rsa", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*password.*", re.IGNORECASE),
    re.compile(r".*credentials.*", re.IGNORECASE),
]


class FileIntelligence:
    """Manages authorized folders, deterministic search, and token-efficient file reading."""

    @classmethod
    def load_authorized_paths(cls) -> list[Path]:
        paths = _get_default_authorized_roots()
        if _PERMISSIONS_FILE.exists():
            try:
                data = json.loads(_PERMISSIONS_FILE.read_text(encoding="utf-8"))
                for p_str in data.get("authorized_folders", []):
                    p = Path(p_str)
                    if p.exists() and p not in paths:
                        paths.append(p)
            except Exception:
                pass
        return paths

    @classmethod
    def authorize_folder(cls, folder_path: str) -> bool:
        p = Path(folder_path).resolve()
        if not p.exists() or not p.is_dir():
            return False
        paths = cls.load_authorized_paths()
        if p not in paths:
            paths.append(p)
            try:
                _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                _PERMISSIONS_FILE.write_text(
                    json.dumps({"authorized_folders": [str(x) for x in paths]}, indent=2),
                    encoding="utf-8"
                )
            except Exception:
                pass
        return True

    @classmethod
    def is_path_authorized(cls, path: Path) -> bool:
        res = path.resolve()
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(res.name):
                return False
        return any(res == root.resolve() or res.is_relative_to(root.resolve()) for root in cls.load_authorized_paths())

    @classmethod
    def search_authorized_files(
        cls,
        query: str,
        file_ext: Optional[str] = None,
        max_results: int = 10,
    ) -> list[dict]:
        """Deterministically search authorized folders without wasting AI tokens."""
        results = []
        tokens = [t.lower() for t in query.split() if len(t) > 1]
        roots = cls.load_authorized_paths()

        for root in roots:
            try:
                for entry in root.rglob("*"):
                    if entry.is_file() and cls.is_path_authorized(entry):
                        # Filter by extension if requested
                        if file_ext and not entry.suffix.lower() == (f".{file_ext.lstrip('.').lower()}"):
                            continue

                        name_lower = entry.name.lower()
                        # Calculate match score based on query tokens
                        matches = sum(1 for t in tokens if t in name_lower)
                        if matches > 0 or not tokens:
                            score = matches / (len(tokens) or 1)
                            results.append({
                                "name": entry.name,
                                "path": str(entry),
                                "size_bytes": entry.stat().st_size,
                                "modified": entry.stat().st_mtime,
                                "score": score,
                            })
                            if len(results) >= max_results * 3:
                                break
            except Exception:
                continue

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]

    @classmethod
    def read_document_excerpt(
        cls,
        file_path: str,
        query: str = "",
        max_chars: int = 1800,
    ) -> dict:
        """Extract relevant excerpt from document (.docx, .pdf, .txt, .md, .py).

        Prevents context bloating by extracting only relevant sections or head/tail summaries.
        """
        p = Path(file_path).resolve()
        if not p.exists():
            return {"ok": False, "error": f"File not found: {file_path}"}

        if not cls.is_path_authorized(p):
            return {"ok": False, "error": f"Access denied: {p} is outside authorized folders or is a protected file."}

        content = ""
        suffix = p.suffix.lower()

        try:
            # Word .docx
            if suffix == ".docx":
                try:
                    import docx
                    doc = docx.Document(p)
                    content = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                except Exception as e:
                    return {"ok": False, "error": f"Error reading Word document: {e}"}

            # PDF
            elif suffix == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(p)
                    pages_text = []
                    for page in reader.pages[:15]:
                        t = page.extract_text()
                        if t:
                            pages_text.append(t)
                    content = "\n".join(pages_text)
                except Exception:
                    content = f"[PDF file: {p.name} - text extraction unavailable]"

            # Standard text/code files (.txt, .md, .py, .json, .csv, etc.)
            else:
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    return {"ok": False, "error": f"Could not read text: {e}"}

        except Exception as e:
            return {"ok": False, "error": f"Failed to open file: {e}"}

        if not content:
            return {"ok": True, "file": p.name, "excerpt": "[Empty document]", "total_chars": 0}

        # If query specified, locate the most relevant matching section
        if query:
            q_lower = query.lower()
            idx = content.lower().find(q_lower)
            if idx != -1:
                start = max(0, idx - 200)
                end = min(len(content), idx + max_chars - 200)
                excerpt = content[start:end]
                return {
                    "ok": True,
                    "file": p.name,
                    "path": str(p),
                    "excerpt": f"...{excerpt}...",
                    "matched": True,
                    "total_chars": len(content),
                }

        # Default to clean leading excerpt
        truncated = content[:max_chars]
        if len(content) > max_chars:
            truncated += f"\n\n[... Remaining {len(content) - max_chars} characters truncated to preserve context ...]"

        return {
            "ok": True,
            "file": p.name,
            "path": str(p),
            "excerpt": truncated,
            "matched": False,
            "total_chars": len(content),
        }


def file_intelligence(
    parameters: dict,
    player=None,
    speak: Optional[Callable[[str], None]] = None,
) -> str:
    """Tool entry point for file search and document intelligence."""
    action = parameters.get("action", "search").lower().strip()
    query = parameters.get("query") or parameters.get("filename") or ""
    path = parameters.get("path") or parameters.get("file_path") or ""

    if action in ("authorize", "add_folder"):
        if not path:
            return "Please provide a folder path to authorize."
        ok = FileIntelligence.authorize_folder(path)
        return f"Authorized folder: {path}" if ok else f"Could not authorize folder: {path}"

    elif action in ("list_folders", "permissions"):
        roots = FileIntelligence.load_authorized_paths()
        return "Authorized folders:\n" + "\n".join([f"- {r}" for r in roots])

    elif action in ("read", "inspect", "excerpt"):
        if not path:
            return "Please provide a file path to read."
        res = FileIntelligence.read_document_excerpt(path, query=query)
        if not res.get("ok"):
            return f"Error: {res.get('error')}"
        return f"File: {res.get('file')} ({res.get('total_chars')} chars):\n\n{res.get('excerpt')}"

    else:  # "search", "find"
        if not query:
            return "Please provide a file name or topic to search for."
        ext = parameters.get("file_ext")
        matches = FileIntelligence.search_authorized_files(query, file_ext=ext, max_results=5)
        if not matches:
            return f"No matching files found for '{query}' in authorized folders."

        lines = [f"Found {len(matches)} matching file(s):"]
        for m in matches:
            size_kb = m["size_bytes"] / 1024
            lines.append(f"- {m['name']} ({size_kb:.1f} KB) -> {m['path']}")
        return "\n".join(lines)
