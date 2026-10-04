#!/usr/bin/env python3
"""Shared helpers for BOOKLIST-driven fetch adapters."""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from paths import corpus_root, download_tmp, project_root, raw_dir

UA = "shi-shi-qiu-shi-corpus-bot/0.2 (personal research)"
ROOT = project_root()
RAW = raw_dir()
TMP = download_tmp()


def bind(corpus: Path | str | None = None) -> Path:
    """Point fetch/write at a corpus tree (cold start / skill pack)."""
    global ROOT, RAW, TMP
    c = corpus_root(corpus)
    ROOT = project_root(c)
    RAW = raw_dir(c)
    TMP = download_tmp(c)
    return c


def install_proxy_from_env() -> str | None:
    proxy = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        urllib.request.install_opener(urllib.request.build_opener(handler))
    return proxy


def fetch_bytes(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read()


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "path"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self.SKIP:
            self._skip_depth += 1
        if tag.lower() in {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "section"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def html_to_text(raw_html: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    parser = TextExtractor()
    parser.feed(cleaned)
    text = html_lib.unescape(parser.text()).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    blank = 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank <= 2:
                out.append("")
            continue
        blank = 0
        out.append(ln)
    return "\n".join(out).strip() + "\n"


def meta_to_yaml(meta: dict) -> str:
    lines = []
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def write_book(book_id: str, filename: str, body: str, meta: dict) -> Path:
    d = RAW / book_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    path.write_text(body, encoding="utf-8")
    meta = dict(meta)
    meta.setdefault("book_id", book_id)
    meta.setdefault("preferred_text", filename)
    meta.setdefault("ingest_status", "ready")
    meta.setdefault("char_count", len(body))
    (d / "META.yaml").write_text(meta_to_yaml(meta), encoding="utf-8")
    return path


def has_preferred_text(book: dict) -> bool:
    bid = book["book_id"]
    pref = book.get("preferred_text")
    d = RAW / bid
    if pref and (d / pref).exists():
        return True
    return any(d.glob("*.txt")) if d.exists() else False
