from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class ConversionResult:
    html: str
    assets: List[Dict[str, str]]
    engine: str


class ConversionError(Exception):
    pass


class PandocConverter:
    def __init__(self, timeout_sec: int = 180):
        self.timeout_sec = timeout_sec
        self._pandoc_path = self._detect_pandoc()

    def _detect_pandoc(self) -> str:
        try:
            out = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=10)
            if out.returncode == 0:
                return "pandoc"
        except Exception as e:
            raise ConversionError(f"Pandoc not available: {e}")
        raise ConversionError("Pandoc not available in PATH")

    def convert(self, docx_path: Path, media_out_dir: Path, mathjax: bool = True) -> ConversionResult:
        if not docx_path.exists():
            raise ConversionError(f"File not found: {docx_path}")

        media_out_dir.mkdir(parents=True, exist_ok=True)

        args = [
            self._pandoc_path,
            "--from",
            "docx",
            "--to",
            "html5",
            "--wrap",
            "none",
            "--extract-media",
            str(media_out_dir),
        ]

        if mathjax:
            args.extend(["--mathjax"])

        args.append(str(docx_path))

        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=self.timeout_sec)
        except subprocess.TimeoutExpired as e:
            raise ConversionError(f"Pandoc timed out after {self.timeout_sec}s") from e
        except Exception as e:
            raise ConversionError(f"Pandoc execution failed: {e}") from e

        if proc.returncode != 0:
            raise ConversionError(f"Pandoc failed: {proc.stderr.strip()}")

        html = proc.stdout

        # Collect extracted assets under media_out_dir
        assets: List[Dict[str, str]] = []
        for p in media_out_dir.rglob("*"):
            if p.is_file():
                assets.append({"local_path": str(p), "name": p.name})

        return ConversionResult(html=html, assets=assets, engine="pandoc")

