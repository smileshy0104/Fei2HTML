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
    html = wrap_tables_with_container(html)
    html = paragraphs_to_lists(html)
    html = ensure_img_lazy_and_strip_inline_styles(html)
    html = add_heading_ids(html)
    return html


def paragraphs_to_lists(html: str) -> str:
    """
    将连续“项目符号/编号”的段落 <p>... 转为 <ul>/<ol><li>...</li>。
    - 仅在出现连续 >=2 个同类条目时才触发（降低误判）。
    - 简单排除：在 <table>...</table> 内不处理。
    支持的前缀：
      • ● ○ ◦ · 以及 "- ", "* ";
      数字/中文数字 + . 或 、 或 ) 或 ）：如 "1. ", "1) ", "1、", "（一）"、"(1)"。
    """
    # Tokenize by <p>...</p> boundaries (retain delimiters)
    parts = re.split(r"(<p\b[^>]*>.*?</p>)", html, flags=re.I | re.S)
    out = []
    i = 0
    in_table = 0
    in_list = False
    list_type = None  # 'ul' or 'ol'

    def classify(text: str):
        t = re.sub(r"<[^>]+>", "", text).strip()
        # Bullet symbols
        if re.match(r"^(•|●|○|◦|·)\s+", t):
            return 'ul', re.sub(r"^(•|●|○|◦|·)\s+", "", t)
        if re.match(r"^(-|\*)\s+", t):
            return 'ul', re.sub(r"^(-|\*)\s+", "", t)
        # Numbered (Arabic or Chinese numerals)
        if re.match(r"^\d+[\.、\)]\s+", t):
            return 'ol', re.sub(r"^\d+[\.、\)]\s+", "", t)
        if re.match(r"^[\(（](\d+|[一二三四五六七八九十]+)[\)）]\s+", t):
            return 'ol', re.sub(r"^[\(（](\d+|[一二三四五六七八九十]+)[\)）]\s+", "", t)
        if re.match(r"^[一二三四五六七八九十]+[、]\s+", t):
            return 'ol', re.sub(r"^[一二三四五六七八九十]+[、]\s+", "", t)
        return None, None

    while i < len(parts):
        seg = parts[i]
        # Track table enter/exit
        if re.search(r"<table\b", seg, flags=re.I):
            in_table += 1
        if re.search(r"</table>", seg, flags=re.I):
            in_table = max(0, in_table - 1)

        m = re.match(r"^<p\b[^>]*>(.*?)</p>$", seg, flags=re.I | re.S)
        if not m:
            # Non-paragraph segment
            # Close any open list before emitting a block element that is not <p>
            if in_list and re.search(r"<(?:div|h[1-6]|table|ul|ol|blockquote|pre)\b", seg, flags=re.I):
                out.append(f"</{list_type}>")
                in_list = False
                list_type = None
            out.append(seg)
            i += 1
            continue

        inner = m.group(1)
        if in_table > 0:
            # Don't convert inside table cells
            if in_list:
                out.append(f"</{list_type}>")
                in_list = False
                list_type = None
            out.append(seg)
            i += 1
            continue

        kind, item_text = classify(inner)
        if not kind:
            # Close list if open
            if in_list:
                out.append(f"</{list_type}>")
                in_list = False
                list_type = None
            out.append(seg)
            i += 1
            continue

        # Lookahead to ensure at least 2 consecutive items of same type
        if not in_list:
            # Peek next paragraph
            next_is_same = False
            if i + 2 < len(parts):
                m2 = re.match(r"^<p\b[^>]*>(.*?)</p>$", parts[i+2], flags=re.I | re.S)
                if m2:
                    k2, _ = classify(m2.group(1))
                    next_is_same = (k2 == kind)
            if not next_is_same:
                # Not enough to be a list; keep as-is
                out.append(seg)
                i += 1
                continue
            # Open list
            out.append(f"<{kind}>")
            in_list = True
            list_type = kind

        # Append item
        out.append(f"<li>{item_text}</li>")
        i += 1

        # If next paragraph is not same kind, close list in next loop iteration
        # (Handled at top when non-list paragraph encountered.)

    # Close any dangling list
    if in_list:
        out.append(f"</{list_type}>")
    return "".join(out)
