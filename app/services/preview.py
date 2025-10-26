from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PreviewInfo:
    path: str
    url: str


def generate_preview_html(
    doc_id: str,
    title: Optional[str],
    html_fragment: str,
    output_dir: Path = Path("out/previews"),
    css_path: Path = Path("app/templates/article.css"),
) -> Optional[PreviewInfo]:
    """Generate a standalone HTML preview file for a converted document.

    Returns the relative path (str) to the generated file, or None if doc_id missing.
    """

    if not doc_id:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    css_text = ""
    if css_path.exists():
        css_text = css_path.read_text(encoding="utf-8")

    safe_title = title or doc_id

    # Adjust asset paths so the preview can be served statically from /out
    preview_html = html_fragment.replace('src="/assets/', 'src="../../assets/')

    full_html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{safe_title}</title>
    <style>
      body {{ margin: 0; background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans'; }}
      .page {{ max-width: 860px; margin: 24px auto; padding: 16px; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
      {css_text}
    </style>
  </head>
  <body>
    <div class="page">
      <div style="margin-bottom:16px;color:#666;">{safe_title}</div>
      {preview_html}
    </div>
  </body>
</html>"""

    doc_dir = output_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    output_path = doc_dir / "index.html"
    output_path.write_text(full_html, encoding="utf-8")

    # Relative URL assuming static server root at project root
    url = f"/out/previews/{doc_id}/"

    return PreviewInfo(path=str(output_path), url=url)
