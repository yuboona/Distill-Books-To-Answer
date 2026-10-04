#!/usr/bin/env python3
"""Clean Phase A texts from local cache snapshots into corpus/raw."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
CACHE = Path("/Users/zhangzhe/.cursor/projects/Users-zhangzhe-ai-career-90d/agent-tools")

SOURCES = {
    "on_practice": CACHE / "fe7f8076-15ef-4b1b-bdf4-030ad5d812bc.txt",
    "on_contradiction": CACHE / "c3d2d141-29a9-49a3-9d23-0f139ebde4f2.txt",
    "sunzi": CACHE / "a357fc7e-4a04-46f2-9044-6137a6177eae.txt",
    "dao_de_jing": CACHE / "63568102-5be1-41a2-a432-d2b5e90788cc.txt",
    "the_prince": CACHE / "d0753979-9164-456d-b86a-79bdd16a1c6a.txt",
    "meditations": CACHE / "50cc9035-40d4-4758-bdff-f61465479415.txt",
}


def meta_to_yaml(meta: dict) -> str:
    lines = []
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def normalize(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def write_book(book_id: str, filename: str, body: str, meta: dict) -> None:
    d = RAW / book_id
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(normalize(body), encoding="utf-8")
    (d / "META.yaml").write_text(meta_to_yaml(meta), encoding="utf-8")
    print(f"wrote {d / filename} ({(d / filename).stat().st_size} bytes)")


def clean_mao(text: str, title: str) -> str:
    text = re.sub(r"(?m)^Title:.*\n", "", text)
    text = re.sub(r"(?m)^URL:.*\n", "", text)
    text = re.sub(r"(?m)^Content:.*\n", "", text)
    idx = text.find(title)
    if idx >= 0:
        text = text[idx:]
    # Drop leading editorial blockquotes (Marxists headnotes)
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    # keep title lines, skip > notes until normal paragraph
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith(">"):
            i += 1
            continue
        # skip blank lines immediately wrapped around notes near top
        out.append(ln)
        i += 1
    text = "\n".join(out)
    for marker in ["Marxists Internet Archive", "马克思主义文库"]:
        j = text.rfind(marker)
        if j > len(text) * 0.8:
            text = text[:j]
    return text


def clean_sunzi(text: str) -> str:
    for noise in [
        "孙子兵法 - 维基文库，自由的图书馆",
        "另见《孙子略解》、《孙子集注》",
    ]:
        text = text.replace(noise, "")
    m = re.search(r"(始计|計篇|孙子曰：兵者)", text)
    if m:
        text = text[m.start() :]
    cut = text.find("又按")
    if cut > 0:
        text = text[:cut]
    text = re.sub(r"(?m)^(目录|分类|导航|工具|检索|编辑).*$", "", text)
    return text


def clean_ddj(text: str) -> str:
    text = re.sub(r"(?m)^老子 \(汇校版\).*", "", text)
    text = re.sub(r"(?m)^维基文库.*", "", text)
    # Prefer Dao section start (帛书/汇校可能作「道，可道也」)
    markers = ["## 道经", "道，可道也", "道可道", "上善若水"]
    start = -1
    for m in markers:
        i = text.find(m)
        if i >= 0:
            start = i if start < 0 else min(start, i)
    # If both 道经 and later content, start at 道经 if present
    i_dao = text.find("## 道经")
    if i_dao >= 0:
        start = i_dao
    if start >= 0:
        text = text[start:]
    lines = []
    for ln in text.splitlines():
        if ln.count("|") >= 3 and len(re.findall(r"[\u4e00-\u9fff]", ln)) < 8:
            continue
        if ln.strip() in {"检索", "编辑", "工具"}:
            continue
        lines.append(ln)
    return "\n".join(lines)


def slice_gutenberg(text: str, starts: list[str], ends: list[str]) -> str:
    """Prefer the LAST plausible start marker (skip TOC)."""
    start = 0
    for s in starts:
        idx = 0
        last = -1
        while True:
            i = text.find(s, idx)
            if i < 0:
                break
            last = i
            idx = i + 1
        if last >= 0:
            start = last
            break
    # Special: The Prince body after 'All states'
    as_idx = text.find("All states, all powers")
    if as_idx >= 0:
        # rewind to preceding CHAPTER I if nearby
        ch = text.rfind("CHAPTER I.", 0, as_idx)
        if ch >= 0 and as_idx - ch < 500:
            start = ch
        else:
            start = max(0, as_idx - 120)
    end = len(text)
    for e in ends:
        i = text.find(e, start + 500)
        if i >= 0:
            end = min(end, i)
    body = text[start:end]
    body = re.sub(r"\*\*\* START OF.*\*\*\*", "", body)
    body = re.sub(r"\*\*\* END OF.*\*\*\*", "", body)
    return body


def main() -> None:
    # 实践论
    write_book(
        "on_practice",
        "实践论.txt",
        clean_mao(SOURCES["on_practice"].read_text(encoding="utf-8"), "实践论"),
        {
            "book_id": "on_practice",
            "title": "实践论",
            "title_en": "On Practice",
            "box": "epistemology",
            "language": "zh",
            "edition_note": "Cleaned from Marxists.org Chinese HTML snapshot",
            "source_url": "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-193707.htm",
            "license": "source-noted; personal research corpus",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )

    write_book(
        "on_contradiction",
        "矛盾论.txt",
        clean_mao(SOURCES["on_contradiction"].read_text(encoding="utf-8"), "矛盾论"),
        {
            "book_id": "on_contradiction",
            "title": "矛盾论",
            "title_en": "On Contradiction",
            "box": "epistemology",
            "language": "zh",
            "edition_note": "Cleaned from Marxists.org Chinese HTML snapshot",
            "source_url": "https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-193708.htm",
            "license": "source-noted; personal research corpus",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )

    write_book(
        "sunzi",
        "孙子兵法.txt",
        clean_sunzi(SOURCES["sunzi"].read_text(encoding="utf-8")),
        {
            "book_id": "sunzi",
            "title": "孙子兵法",
            "title_en": "The Art of War",
            "box": "strategy",
            "language": "classical_zh",
            "edition_note": "Cleaned from Wikisource Chinese page snapshot; appendix trimmed",
            "source_url": "https://zh.wikisource.org/zh-hans/%E5%AD%AB%E5%AD%90%E5%85%B5%E6%B3%95",
            "license": "public-domain classical text via Wikisource",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )

    write_book(
        "dao_de_jing",
        "道德经.txt",
        clean_ddj(SOURCES["dao_de_jing"].read_text(encoding="utf-8")),
        {
            "book_id": "dao_de_jing",
            "title": "道德经",
            "title_en": "Dao De Jing",
            "box": "cultivation",
            "language": "classical_zh",
            "edition_note": "Cleaned from Wikisource 汇校版 snapshot",
            "source_url": "https://zh.wikisource.org/zh-hans/%E8%80%81%E5%AD%90_(%E5%8C%AF%E6%A0%A1%E7%89%88)",
            "license": "public-domain classical text via Wikisource",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "zh",
        },
    )

    prince = slice_gutenberg(
        SOURCES["the_prince"].read_text(encoding="utf-8"),
        starts=["DEDICATION", "To the Magnificent Lorenzo", "CHAPTER I."],
        ends=[
            "DESCRIPTION OF THE METHODS ADOPTED BY THE DUKE VALENTINO",
            "THE LIFE OF CASTRUCCIO",
            "*** END OF THE PROJECT GUTENBERG",
        ],
    )
    write_book(
        "the_prince",
        "the_prince_marriott.txt",
        prince,
        {
            "book_id": "the_prince",
            "title": "君主论",
            "title_en": "The Prince",
            "box": "strategy",
            "language": "en",
            "edition_note": "Project Gutenberg #1232 W.K. Marriott English; retrieval in EN, answers in ZH",
            "source_url": "https://www.gutenberg.org/ebooks/1232",
            "license": "public-domain (Project Gutenberg / US)",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "en",
            "retrieval_note": "Retrieve English source quotes; counsel in Chinese; never invent Chinese as if it were the source wording.",
        },
    )

    med = slice_gutenberg(
        SOURCES["meditations"].read_text(encoding="utf-8"),
        starts=["THE FIRST BOOK", "I. Of my grandfather Verus", "FIRST BOOK"],
        ends=["APPENDIX", "GLOSSARY", "*** END OF THE PROJECT GUTENBERG"],
    )
    write_book(
        "meditations",
        "meditations_pg2680.txt",
        med,
        {
            "book_id": "meditations",
            "title": "沉思录",
            "title_en": "Meditations",
            "box": "cultivation",
            "language": "en",
            "edition_note": "Project Gutenberg #2680 English; retrieval in EN, answers in ZH",
            "source_url": "https://www.gutenberg.org/ebooks/2680",
            "license": "public-domain (Project Gutenberg / US)",
            "ingest_status": "ready",
            "answer_language": "zh",
            "retrieval_language": "en",
            "retrieval_note": "Retrieve English source quotes; counsel in Chinese.",
        },
    )


if __name__ == "__main__":
    main()
