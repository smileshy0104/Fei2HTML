from __future__ import annotations

import re
from pathlib import Path


_P_STRONG_ONLY_RE = re.compile(r"<p>\s*<strong>(.*?)</strong>\s*</p>", re.I | re.S)
_IMG_STYLE_RE = re.compile(r"(<img\b[^>]*?)\s+style=\"[^\"]*\"([^>]*>)", re.I)
_IMG_TAG_RE = re.compile(r"<img\b([^>]*?)>", re.I)
_TABLE_OPEN_RE = re.compile(r"<table\b", re.I)
_TABLE_CLOSE_RE = re.compile(r"</table>", re.I)
_SRC_RE = re.compile(r"src=(['\"])([^'\"]+)\1", re.I)


def _slugify(text: str) -> str:
    s = re.sub(r"\s+", "-", text.strip())
    s = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", s, flags=re.UNICODE)
    return s[:80] or "section"


def promote_strong_paragraphs_to_headings(html: str) -> str:
    def repl(m: re.Match) -> str:
        content = m.group(1).strip()
        # Heuristic: if content is not too long or looks numbered, treat as heading
        is_numbered = re.match(r"^\s*\d+(?:[\.\d]*)?\s+", content)
        if is_numbered or len(content) <= 80:
            hid = _slugify(content)
            return f'<h2 id="{hid}">{content}</h2>'
        return m.group(0)

    return _P_STRONG_ONLY_RE.sub(repl, html)


def ensure_img_lazy_and_strip_inline_styles(html: str) -> str:
    # Remove inline style on img
    html = _IMG_STYLE_RE.sub(r"\1\2", html)

    # Ensure loading="lazy"
    def img_repl(m: re.Match) -> str:
        attrs = m.group(1)
        if re.search(r"\bloading=", attrs, re.I) is None:
            attrs = attrs.rstrip() + ' loading="lazy"'
        return f"<img{attrs}>"

    return _IMG_TAG_RE.sub(img_repl, html)


def wrap_tables_with_container(html: str) -> str:
    # Wrap each <table>...</table> with a div.table-wrap
    # Simple linear replace; assumes tables are not nested (common for docs)
    html = _TABLE_OPEN_RE.sub('<div class="table-wrap"><table', html)
    html = _TABLE_CLOSE_RE.sub('</table></div>', html)
    return html


def add_heading_ids(html: str) -> str:
    # For any h1-h6 without id, generate one from text
    def repl(m: re.Match) -> str:
        tag = m.group(1)
        attrs = m.group(2)
        inner = m.group(3)
        if re.search(r"\bid=\"", attrs, re.I):
            return m.group(0)
        hid = _slugify(re.sub(r"<[^>]+>", "", inner))
        return f"<{tag} id=\"{hid}\"{attrs}>{inner}</{tag}>"

    pattern = re.compile(r"<(h[1-6])(\b[^>]*)>(.*?)</h[1-6]>", re.I | re.S)
    return pattern.sub(repl, html)


def process_all(html: str) -> str:
    html = promote_strong_paragraphs_to_headings(html)
    html = add_heading_ids(html)
    html = wrap_tables_with_container(html)
    html = ensure_img_lazy_and_strip_inline_styles(html)
    return html

