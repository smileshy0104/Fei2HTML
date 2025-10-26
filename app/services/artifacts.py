from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Optional


def write_asset_manifest(
    doc_id: Optional[str],
    engine: str,
    assets: List[Dict[str, str]],
    output_dir: Path = Path("out"),
) -> Optional[str]:
    """Persist asset manifest as JSON for offline usage.

    Returns the string path if written; otherwise None.
    """

    if not doc_id:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"{doc_id}.assets.json"
    payload = {
        "engine": engine,
        "assets": assets,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(manifest_path)

