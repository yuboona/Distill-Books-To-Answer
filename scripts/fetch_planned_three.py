#!/usr/bin/env python3
"""Fetch 盐铁论 / 传习录 / 毛选方法篇 into corpus/raw.

Uses HTTP(S)_PROXY if set (recommended: http://127.0.0.1:7890).
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
TMP = ROOT / ".download_tmp"
UA = "shi-shi-qiu-shi-corpus-bot/0.1 (personal research)"

# Honor env proxy (curl-style)
_proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("http_proxy")
if _proxy:
    handler = urllib.request.ProxyHandler({"http": _proxy, "https": _proxy})
    urllib.request.install_opener(urllib.request.build_opener(handler))


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=180) as resp:
        return resp.read()


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_text(url: str) -> str:
    return decode_bytes(fetch(url))


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


def write_book(book_id: str, filename: str, body: str, meta: dict) -> Path:
    d = RAW / book_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    path.write_text(body, encoding="utf-8")
    (d / "META.yaml").write_text(meta_to_yaml(meta), encoding="utf-8")
    print(f"OK {book_id}: {path} ({path.stat().st_size} bytes, {len(body)} chars)")
    return path


def clean_marxists(text: str, title: str) -> str:
    idx = text.find(title)
    if idx >= 0:
        text = text[idx:]
    for stop in [
        "马克思 主义文库",
        "马克思主义文库",
        "Marxists Internet Archive",
        "Selected Works of Mao Tse-tung",
    ]:
        j = text.rfind(stop)
        if j > len(text) * 0.6:
            text = text[:j]
    return normalize(text)


# ---------- 盐铁论 ----------
def fetch_yan_tie_lun() -> None:
    """kanripo KR3a0006 classical text (avoid bilingual mirrors with 译文)."""
    TMP.mkdir(parents=True, exist_ok=True)
    kr = TMP / "yantie_kr"
    kr.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    for i in range(1, 13):
        name = f"KR3a0006_{i:03d}.txt"
        cache = kr / name
        url = f"https://raw.githubusercontent.com/kanripo/KR3a0006/master/{name}"
        if not cache.exists():
            cache.write_bytes(fetch(url))
        t = cache.read_text(encoding="utf-8", errors="replace")
        lines = []
        for ln in t.splitlines():
            if ln.startswith("#+") or ln.startswith("# -*-"):
                continue
            ln = re.sub(r"<pb:[^>]+>", "", ln)
            ln = ln.replace("¶", "")
            lines.append(ln)
        parts.append(f"\n\n===== 卷{i:03d} =====\n\n" + "\n".join(lines).strip() + "\n")
    text = normalize("盐铁论\n汉 桓宽 撰（kanripo KR3a0006）\n" + "".join(parts))
    if text.count("大夫曰") < 50:
        raise RuntimeError("盐铁论 body looks incomplete")
    write_book(
        "yan_tie_lun",
        "盐铁论.txt",
        text,
        {
            "book_id": "yan_tie_lun",
            "title": "盐铁论",
            "title_en": "Discourses on Salt and Iron",
            "box": "policy_debate",
            "language": "classical_zh",
            "edition_note": "kanripo KR3a0006 volumes 001-012 (WYG/SBCK lineage); includes 张之象注 parentheses",
            "source_url": "https://github.com/kanripo/KR3a0006",
            "license": "classical public-domain text via Kanseki Repository; personal research",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
            "preferred_text": "盐铁论.txt",
            "source_adapter": "kanripo_volumes",
            "char_count": len(text),
        },
    )


# ---------- 传习录 ----------
def fetch_chuanxilu() -> None:
    url = (
        "https://raw.githubusercontent.com/qinxiaozhi/dzg2.0/master/"
        "%E5%84%92%E8%97%8F/%E8%AF%AD%E5%BD%95/%E4%BC%A0%E4%B9%A0%E5%BD%95.txt"
    )
    TMP.mkdir(parents=True, exist_ok=True)
    cache = TMP / "chuanxilu_dzg.txt"
    if not cache.exists():
        cache.write_bytes(fetch(url))
    text = cache.read_text(encoding="utf-8", errors="replace")
    # Normalize BOM / leading title
    text = text.lstrip("\ufeff")
    if "知行" not in text and "先生" not in text:
        raise RuntimeError("传习录 body looks empty/wrong")
    text = normalize(text)
    write_book(
        "chuanxilu",
        "传习录.txt",
        text,
        {
            "book_id": "chuanxilu",
            "title": "传习录",
            "title_en": "Instructions for Practical Living",
            "box": "cultivation",
            "language": "classical_zh",
            "edition_note": "Full text from public GitHub classical corpus (dzg2.0 儒藏/语录); verify against Wikisource if citing critically",
            "source_url": "https://github.com/qinxiaozhi/dzg2.0",
            "license": "classical public-domain text via public corpus; personal research",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
            "preferred_text": "传习录.txt",
            "source_adapter": "plain_txt",
            "char_count": len(text),
        },
    )


# ---------- 毛选方法篇 ----------
MAO_ESSAYS = [
    ("反对本本主义", "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-193005.htm"),
    ("改造我们的学习", "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-19410519.htm"),
    ("整顿党的作风", "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-19420201.htm"),
    ("反对党八股", "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-19420208.htm"),
    ("《农村调查》的序言和跋", "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-194134.htm"),
    ("关于领导方法的若干问题", "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-19430601.htm"),
    ("党委会的工作方法", "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-19490313.htm"),
    (
        "人的正确思想是从哪里来的？",
        "http://dangjian.people.com.cn/n/2015/0316/c117092-26697670.html",
    ),
]


def fetch_mao_methods() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    sources: list[str] = []
    essay_ok: list[str] = []
    for title, url in MAO_ESSAYS:
        safe = re.sub(r"[^\w\u4e00-\u9fff]+", "_", title)[:40]
        cache = TMP / f"mao_{safe}.html"
        try:
            if not cache.exists():
                cache.write_bytes(fetch(url))
            raw = decode_bytes(cache.read_bytes())
        except Exception as e:
            print(f"WARN skip {title}: {e}")
            continue
        body = clean_marxists(html_to_text(raw), title[:6])
        for key in [title, title.replace("？", ""), title.replace("《", "").replace("》", "")[:6]]:
            i = body.find(key)
            if i >= 0:
                body = body[i:]
                break
        # people.com.cn pages may wrap content — require epistemic markers
        if title.startswith("人的正确思想") and "社会实践" not in body and "物质" not in body:
            print(f"WARN body suspicious for {title}")
        if len(body) < 200:
            print(f"WARN short {title} ({len(body)})")
            continue
        parts.append(f"\n\n{'=' * 60}\n{title}\n来源: {url}\n{'=' * 60}\n\n{body.strip()}\n")
        sources.append(url)
        essay_ok.append(title)
        print(f"  + {title}: {len(body)} chars")

    if len(parts) < 5:
        raise RuntimeError(f"too few Mao essays fetched: {len(parts)}")
    text = normalize("毛选方法篇选（个人研究语料）\n" + "".join(parts))
    write_book(
        "mao_selected_methods",
        "毛选方法篇选.txt",
        text,
        {
            "book_id": "mao_selected_methods",
            "title": "毛选方法篇选",
            "title_en": "Mao selected method essays",
            "box": "epistemology",
            "language": "zh",
            "edition_note": "Curated method essays (not full Selected Works); Marxists.org + one people.com.cn reprint",
            "source_url": "https://www.marxists.org/chinese/maozedong/",
            "source_urls": sources,
            "license": "source-noted; personal research corpus",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
            "preferred_text": "毛选方法篇选.txt",
            "source_adapter": "marxists_html",
            "essays": essay_ok,
            "char_count": len(text),
        },
    )


def main() -> None:
    print(f"proxy={_proxy or '(none)'}")
    fetch_yan_tie_lun()
    fetch_chuanxilu()
    fetch_mao_methods()
    print("done")


if __name__ == "__main__":
    main()
