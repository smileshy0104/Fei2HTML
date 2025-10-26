from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.converters.pandoc_converter import PandocConverter, ConversionResult, ConversionError
from app.services.image_store import ImageStore
from app.services.html_postprocess import process_all
import re


@dataclass
class HybridResult:
    html: str
    assets: List[Dict[str, str]]
    engine: str


class HybridConverter:
    def __init__(self, image_store: ImageStore, timeout_sec: int = 180):
        self.image_store = image_store
        self.timeout_sec = timeout_sec

    def convert_docx(self, docx_path: Path, doc_id: Optional[str] = None) -> HybridResult:
        doc_id = doc_id or docx_path.stem

        # Try Pandoc first
        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = Path(tmpdir) / "media"
            converter = PandocConverter(timeout_sec=self.timeout_sec)
            result = converter.convert(docx_path=docx_path, media_out_dir=media_dir)

            # Upload assets and rewrite HTML <img> src
            uploads: List[Dict[str, str]] = []
            local_to_url: Dict[str, str] = {}
            for idx, asset in enumerate(result.assets):
                local = Path(asset["local_path"]).resolve()
                if not local.exists():
                    continue
                dest_rel = Path(doc_id) / local.name
                url = self.image_store.save(local, dest_rel)
                uploads.append({"name": asset["name"], "url": url})
                local_to_url[str(local)] = url

            html = self._rewrite_img_srcs(result.html, local_to_url)
            html = process_all(html)
            return HybridResult(html=html, assets=uploads, engine=result.engine)

    def _rewrite_img_srcs(self, html: str, mapping: Dict[str, str]) -> str:
        # Build a filename->url map for best-effort replacement
        name_map: Dict[str, str] = {}
        for k, v in mapping.items():
            name_map[Path(k).name] = v

        # Regex to find img src values
        def repl(match):
            quote = match.group(1)
            src = match.group(2)
            filename = Path(src).name
            new = name_map.get(filename)
            if new:
                return f"src={quote}{new}{quote}"
            return match.group(0)

        pattern = re.compile(r"src=(['\"])([^'\"]+)\1", re.IGNORECASE)
        return pattern.sub(repl, html)
