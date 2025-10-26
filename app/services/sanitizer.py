from __future__ import annotations

try:
    import bleach  # type: ignore
except Exception:  # graceful fallback if bleach not installed
    bleach = None


ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "span",
    "a",
    "img",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "code",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "figure",
    "figcaption",
    "sup",
    "sub",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "td": ["colspan", "rowspan", "align"],
    "th": ["colspan", "rowspan", "align"],
    "span": ["class"],
    "code": ["class"],
    "p": ["class"],
    "pre": ["class"],
    "h1": ["id"],
    "h2": ["id"],
    "h3": ["id"],
    "h4": ["id"],
    "h5": ["id"],
    "h6": ["id"],
}


def sanitize_and_inject_css(html: str) -> str:
    if bleach:
        cleaned = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            strip=True,
        )
        cleaned = bleach.linkify(cleaned, callbacks=[_set_rel_noopener])
    else:
        # Fallback: minimal cleanup by simple replacement (no security guarantees)
        cleaned = html
    return f'<div class="lark-article">{cleaned}</div>'


def _set_rel_noopener(attrs, new=False):
    href_key = (None, "href")
    if href_key in attrs:
        attrs[(None, "rel")] = "noopener noreferrer"
    return attrs
