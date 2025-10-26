#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.converters.hybrid import HybridConverter
from app.services.image_store import LocalImageStore
from app.services.sanitizer import sanitize_and_inject_css


def main():
    parser = argparse.ArgumentParser(description="Convert .docx to HTML (Pandoc mainline, Mammoth fallback)")
    parser.add_argument("docx", type=str, help="Path to .docx file")
    parser.add_argument("--doc-id", type=str, default=None, help="Logical doc id for asset naming")
    parser.add_argument("--out-html", type=str, default=None, help="Output html path (defaults next to docx)")
    args = parser.parse_args()

    docx_path = Path(args.docx)
    if not docx_path.exists():
        print(f"File not found: {docx_path}", file=sys.stderr)
        return 2

    image_store = LocalImageStore(base_dir=Path("public/assets"), base_url="/assets")
    converter = HybridConverter(image_store=image_store)

    result = converter.convert_docx(docx_path, doc_id=args.doc_id)
    html_clean = sanitize_and_inject_css(result.html)

    out_html = Path(args.out_html) if args.out_html else docx_path.with_suffix(".html")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_clean, encoding="utf-8")

    manifest_path = out_html.with_suffix(".assets.json")
    manifest_path.write_text(json.dumps({"engine": result.engine, "assets": result.assets}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Converted: {docx_path}")
    print(f"HTML: {out_html}")
    print(f"Assets manifest: {manifest_path}")


if __name__ == "__main__":
    raise SystemExit(main())
