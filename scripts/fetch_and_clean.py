#!/usr/bin/env python3
"""Fetch and clean Phase A corpus texts into corpus/raw/<book_id>/."""

from __future__ import annotations

import html as html_lib
import json
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
UA = "shi-shi-qiu-shi-corpus-bot/0.1 (personal research; +local)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
        return resp.read()


class TextExtractor(HTMLParser):
    """Collect visible text; skip script/style/nav-ish tags."""

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
        if self._skip_depth:
            return
        self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def html_to_text(raw_html: str) -> str:
    # Drop mediawiki navigation / reference blocks lightly via regex first
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    parser = TextExtractor()
    parser.feed(cleaned)
    text = html_lib.unescape(parser.text())
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_blank_lines(text: str) -> str:
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


def write_book(book_id: str, filename: str, body: str, meta: dict) -> Path:
    d = RAW / book_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    path.write_text(body, encoding="utf-8")
    (d / "META.yaml").write_text(meta_to_yaml(meta), encoding="utf-8")
    return path


def meta_to_yaml(meta: dict) -> str:
    # Minimal YAML without PyYAML dependency
    lines = []
    for k, v in meta.items():
        if isinstance(v, bool):
            val = "true" if v else "false"
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
            continue
        else:
            val = json.dumps(v, ensure_ascii=False)
        lines.append(f"{k}: {val}")
    return "\n".join(lines) + "\n"


def clean_marxists(text: str, title_marker: str) -> str:
    # Keep from title through notes; drop site chrome if present
    idx = text.find(title_marker)
    if idx >= 0:
        text = text[idx:]
    # Common footer noise
    for stop in ["Marxists Internet Archive", "马克思主义文库", "目录"]:
        # only trim trailing chrome after notes if duplicated
        pass
    # Remove excessive footnote bracket noise kept as content is fine
    text = re.sub(r"\n翻页:.*", "", text)
    return normalize_blank_lines(text)


def fetch_practice() -> None:
    url = "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-193707.htm"
    raw = fetch(url).decode("utf-8", errors="replace")
    text = html_to_text(raw)
    text = clean_marxists(text, "实践论")
    # Prefer body starting at essay title line
    m = re.search(r"实践论[：:].{0,40}知和行的关系", text)
    if m:
        text = text[m.start() :]
    write_book(
        "on_practice",
        "实践论.txt",
        text,
        {
            "book_id": "on_practice",
            "title": "实践论",
            "title_en": "On Practice",
            "box": "epistemology",
            "language": "zh",
            "edition_note": "Marxists Internet Archive Chinese HTML, cleaned to plain text",
            "source_url": url,
            "license": "source-noted; personal research corpus",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )


def fetch_contradiction() -> None:
    url = "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-193708.htm"
    raw = fetch(url).decode("utf-8", errors="replace")
    text = html_to_text(raw)
    text = clean_marxists(text, "矛盾论")
    m = re.search(r"矛盾论", text)
    if m:
        text = text[m.start() :]
    write_book(
        "on_contradiction",
        "矛盾论.txt",
        text,
        {
            "book_id": "on_contradiction",
            "title": "矛盾论",
            "title_en": "On Contradiction",
            "box": "epistemology",
            "language": "zh",
            "edition_note": "Marxists Internet Archive Chinese HTML, cleaned to plain text",
            "source_url": url,
            "license": "source-noted; personal research corpus",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )


def fetch_sunzi() -> None:
    url = "https://zh.wikisource.org/wiki/%E5%AD%AB%E5%AD%90%E5%85%B5%E6%B3%95?action=raw"
    # raw wikitext is cleaner for classics
    try:
        wikitext = fetch(url).decode("utf-8", errors="replace")
    except Exception:
        html_url = "https://zh.wikisource.org/zh-hans/%E5%AD%AB%E5%AD%90%E5%85%B5%E6%B3%95"
        wikitext = html_to_text(fetch(html_url).decode("utf-8", errors="replace"))
        url = html_url
    text = wikitext
    # Strip mediawiki templates lightly
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    text = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    # Drop appendix-ish tail starting with 又按
    cut = text.find("又按")
    if cut > 0 and cut > len(text) * 0.5:
        text = text[:cut]
    text = normalize_blank_lines(text)
    write_book(
        "sunzi",
        "孙子兵法.txt",
        text,
        {
            "book_id": "sunzi",
            "title": "孙子兵法",
            "title_en": "The Art of War",
            "box": "strategy",
            "language": "classical_zh",
            "edition_note": "Wikisource Chinese text; appendix notes stripped when present",
            "source_url": url,
            "license": "public-domain classical text via Wikisource",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )


def fetch_ddj() -> None:
    # Prefer 王弼注 plain text if raw available; fallback 汇校版 html
    candidates = [
        "https://zh.wikisource.org/wiki/%E8%80%81%E5%AD%90?action=raw",
        "https://zh.wikisource.org/wiki/%E9%81%93%E5%BE%B7%E7%B6%93?action=raw",
        "https://zh.wikisource.org/zh-hans/%E8%80%81%E5%AD%90_(%E5%8C%AF%E6%A0%A1%E7%89%88)",
    ]
    text = ""
    used = candidates[0]
    for url in candidates:
        try:
            raw = fetch(url).decode("utf-8", errors="replace")
        except Exception:
            continue
        if "action=raw" in url or raw.lstrip().startswith(("{", "=", "#", "道", "老子")):
            if "<html" in raw.lower():
                body = html_to_text(raw)
            else:
                body = raw
                body = re.sub(r"\{\{[^}]+\}\}", "", body)
                body = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", body)
                body = re.sub(r"'{2,}", "", body)
                body = re.sub(r"<ref[^>]*>.*?</ref>", "", body, flags=re.S)
                body = re.sub(r"<[^>]+>", "", body)
        else:
            body = html_to_text(raw)
        # Heuristic: must contain classic openings
        if "道可道" in body or "上德不德" in body or "天下皆知美之为美" in body:
            text = body
            used = url
            break
    if not text:
        raise RuntimeError("Failed to fetch Dao De Jing text")
    # If page is an index, try wangbi chapter dump via known gutenberg-like - keep what we have
    text = normalize_blank_lines(text)
    write_book(
        "dao_de_jing",
        "道德经.txt",
        text,
        {
            "book_id": "dao_de_jing",
            "title": "道德经",
            "title_en": "Dao De Jing",
            "box": "cultivation",
            "language": "classical_zh",
            "edition_note": "Wikisource classical text (cleaned)",
            "source_url": used,
            "license": "public-domain classical text via Wikisource",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )


def slice_gutenberg(text: str, start_markers: list[str], end_markers: list[str]) -> str:
    start = 0
    for m in start_markers:
        i = text.find(m)
        if i >= 0:
            start = i
            break
    end = len(text)
    for m in end_markers:
        i = text.find(m, start + 100)
        if i >= 0:
            end = min(end, i)
    body = text[start:end]
    # Drop PG header/footer remnants if still present
    body = re.sub(r"\*\*\* START OF.*\*\*\*", "", body)
    body = re.sub(r"\*\*\* END OF.*\*\*\*", "", body)
    return normalize_blank_lines(body)


def fetch_prince() -> None:
    url = "https://www.gutenberg.org/files/1232/1232-0.txt"
    text = fetch(url).decode("utf-8", errors="replace")
    # Keep dedication + chapters of The Prince; drop long bio intro if possible
    body = slice_gutenberg(
        text,
        start_markers=["DEDICATION", "To the Magnificent Lorenzo", "CHAPTER I."],
        end_markers=[
            "DESCRIPTION OF THE METHODS ADOPTED BY THE DUKE VALENTINO",
            "THE LIFE OF CASTRUCCIO",
            "*** END OF THE PROJECT GUTENBERG",
        ],
    )
    # Ensure chapter I present
    if "CHAPTER I" not in body.upper():
        body = slice_gutenberg(
            text,
            start_markers=["CHAPTER I."],
            end_markers=["*** END OF THE PROJECT GUTENBERG"],
        )
    write_book(
        "the_prince",
        "the_prince_marriott.txt",
        body,
        {
            "book_id": "the_prince",
            "title": "君主论",
            "title_en": "The Prince",
            "box": "strategy",
            "language": "en",
            "edition_note": "Project Gutenberg eBook #1232, tr. W. K. Marriott; English body used for retrieval",
            "source_url": url,
            "license": "public-domain (Project Gutenberg / US)",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "en",
            "retrieval_note": "Retrieve English quotes; explain and counsel in Chinese. Do not pretend Chinese wording is the source text.",
        },
    )


def fetch_meditations() -> None:
    url = "https://www.gutenberg.org/cache/epub/2680/pg2680.txt"
    text = fetch(url).decode("utf-8", errors="replace")
    body = slice_gutenberg(
        text,
        start_markers=["THE FIRST BOOK", "FIRST BOOK", "I. Of my grandfather Verus"],
        end_markers=["APPENDIX", "GLOSSARY", "*** END OF THE PROJECT GUTENBERG"],
    )
    write_book(
        "meditations",
        "meditations_pg2680.txt",
        body,
        {
            "book_id": "meditations",
            "title": "沉思录",
            "title_en": "Meditations",
            "box": "cultivation",
            "language": "en",
            "edition_note": "Project Gutenberg eBook #2680 English text; used for retrieval",
            "source_url": url,
            "license": "public-domain (Project Gutenberg / US)",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "en",
            "retrieval_note": "Retrieve English quotes; explain and counsel in Chinese.",
        },
    )


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    steps = [
        ("on_practice", fetch_practice),
        ("on_contradiction", fetch_contradiction),
        ("sunzi", fetch_sunzi),
        ("dao_de_jing", fetch_ddj),
        ("the_prince", fetch_prince),
        ("meditations", fetch_meditations),
    ]
    for name, fn in steps:
        print(f"==> fetching {name}")
        fn()
        p = next((RAW / name).glob("*.txt"))
        print(f"    wrote {p} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
