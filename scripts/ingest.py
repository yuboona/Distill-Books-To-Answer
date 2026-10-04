#!/usr/bin/env python3
"""Ingest corpus/raw → corpus/chunks/<book_id>.jsonl

Respects docs/03-corpus.md:
- Prefer natural structure splits (卷/篇/章)
- Target ~200–600 CJK chars (EN: ~400–1200 chars)
- Fields: id, book_id, locus, text, prev_id, next_id, char_count
  (+ source_file, retrieval_language)

Usage:
  python3 scripts/ingest.py
  python3 scripts/ingest.py --only on_practice,sunzi
  python3 scripts/ingest.py --booklist corpus/BOOKLIST.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import chunks_dir, corpus_root, project_root, raw_dir  # noqa: E402

ROOT = project_root()
RAW = raw_dir()
CHUNKS = chunks_dir()


def bind(corpus: Path | str | None = None) -> Path:
    global ROOT, RAW, CHUNKS
    c = corpus_root(corpus)
    ROOT = project_root(c)
    RAW = raw_dir(c)
    CHUNKS = chunks_dir(c)
    return c

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

PREFERRED_TEXT = {
    "shiji": "史记.简体.txt",
    "zizhi_tongjian": "资治通鉴_全文.txt",
    "the_prince": "the_prince_marriott.txt",
    "meditations": "meditations_pg2680.txt",
    "on_practice": "实践论.txt",
    "on_contradiction": "矛盾论.txt",
    "sunzi": "孙子兵法.txt",
    "dao_de_jing": "道德经.txt",
    "yan_tie_lun": "盐铁论.txt",
    "chuanxilu": "传习录.txt",
    "mao_selected_works": "毛泽东选集_1-5卷.txt",
}

# book_id → (min_chars, max_chars) soft targets
SIZE = {
    "default_zh": (200, 600),
    "default_en": (400, 1200),
    "zizhi_tongjian": (300, 800),  # huge; slightly larger slices
    "mao_selected_works": (250, 700),
    "shiji": (250, 700),
}


def load_meta(book_dir: Path) -> dict:
    path = book_dir / "META.yaml"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    meta: dict = {}
    for line in text.splitlines():
        if ":" in line and not line.strip().startswith("-"):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def resolve_source(book_id: str, book_dir: Path, preferred: str | None) -> Path | None:
    if preferred:
        p = book_dir / preferred
        if p.exists():
            return p
    pref = PREFERRED_TEXT.get(book_id)
    if pref and (book_dir / pref).exists():
        return book_dir / pref
    txts = sorted(book_dir.glob("*.txt"))
    # Prefer non-volume aggregate names
    for t in txts:
        if t.parent.name == book_id and "静火" not in t.name:
            return t
    return txts[0] if txts else None


def split_sections(book_id: str, text: str) -> list[tuple[str, str]]:
    """Return list of (locus_hint, section_text)."""
    text = text.replace("\r\n", "\n")

    if book_id == "mao_selected_works":
        # Prefer essay markers
        parts = re.split(r"\n(?=----- .+ -----\n)", text)
        out = []
        for p in parts:
            p = p.strip()
            if len(p) < 40:
                continue
            m = re.match(r"----- (.+?) -----\n", p)
            locus = m.group(1).strip() if m else "mao"
            out.append((locus, p))
        if len(out) >= 10:
            return out

    if book_id == "the_prince":
        parts = re.split(r"(?m)(?=^CHAPTER\s+[IVXLC\d]+)", text)
        out = []
        for p in parts:
            p = p.strip()
            if len(p) < 40:
                continue
            m = re.match(r"(CHAPTER\s+[IVXLC\d]+[^\n]*)", p)
            locus = m.group(1).strip()[:80] if m else "the_prince"
            out.append((locus, p))
        if out:
            return out

    if book_id == "meditations":
        parts = re.split(r"(?m)(?=^BOOK\s+[IVXLC\d]+)", text)
        out = []
        for p in parts:
            p = p.strip()
            if len(p) < 40:
                continue
            m = re.match(r"(BOOK\s+[IVXLC\d]+)", p)
            locus = m.group(1) if m else "meditations"
            out.append((locus, p))
        if out:
            return out

    if book_id in {"zizhi_tongjian", "yan_tie_lun"}:
        parts = re.split(r"\n(?===== )", text)
        out = []
        for p in parts:
            p = p.strip()
            if len(p) < 40:
                continue
            m = re.match(r"===== ([^=]+) =====", p)
            locus = m.group(1).strip() if m else book_id
            out.append((locus, p))
        if len(out) >= 2:
            return out

    if book_id == "sunzi":
        parts = re.split(r"(?m)(?=^\S+\s*第[一二三四五六七八九十]+)", text)
        out = []
        for p in parts:
            p = p.strip()
            if len(p) < 20:
                continue
            first = p.split("\n", 1)[0].strip()[:40]
            out.append((first or "sunzi", p))
        if len(out) >= 5:
            return out

    if book_id == "dao_de_jing":
        # often continuous; treat as one section
        return [("道德经", text.strip())]

    if book_id == "chuanxilu":
        parts = re.split(r"(?m)(?=^　*卷[上中下])", text)
        if len(parts) < 2:
            parts = re.split(r"(?m)(?=^○)", text)
        out = []
        for i, p in enumerate(parts):
            p = p.strip()
            if len(p) < 40:
                continue
            head = p.split("\n", 1)[0].strip()[:40] or f"传习录-{i}"
            out.append((head, p))
        if out:
            return out

    # default: whole book one section
    return [(book_id, text.strip())]


def pack_paragraphs(paras: list[str], min_c: int, max_c: int) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal buf, size
        if not buf:
            return
        chunks.append("\n\n".join(buf).strip())
        buf = []
        size = 0

    for para in paras:
        para = para.strip()
        if not para:
            continue
        if len(para) > max_c:
            flush()
            # hard-split long paragraph
            i = 0
            while i < len(para):
                chunks.append(para[i : i + max_c].strip())
                i += max_c
            continue
        if size + len(para) + 2 <= max_c:
            buf.append(para)
            size += len(para) + 2
        else:
            if size >= min_c or not buf:
                flush()
                buf.append(para)
                size = len(para)
            else:
                # below min but would overflow → flush anyway then start
                flush()
                buf.append(para)
                size = len(para)
    flush()
    # merge tiny trailing chunk into previous when possible
    if len(chunks) >= 2 and len(chunks[-1]) < min_c // 2:
        if len(chunks[-2]) + len(chunks[-1]) + 2 <= max_c + 100:
            chunks[-2] = chunks[-2] + "\n\n" + chunks[-1]
            chunks.pop()
    return [c for c in chunks if c]


def chunk_section(locus: str, section: str, min_c: int, max_c: int) -> list[tuple[str, str]]:
    paras = re.split(r"\n\s*\n", section)
    if len(paras) == 1:
        # single block — also try single newlines as soft breaks for dense classical
        if len(section) > max_c * 2:
            paras = [ln for ln in section.split("\n") if ln.strip()]
    packed = pack_paragraphs(paras, min_c, max_c)
    out = []
    for i, body in enumerate(packed):
        loc = locus if len(packed) == 1 else f"{locus}#{i + 1}"
        out.append((loc, body))
    return out


def link_ids(book_id: str, items: list[tuple[str, str]]) -> list[dict]:
    rows = []
    for i, (locus, text) in enumerate(items):
        cid = f"{book_id}-{i + 1:04d}"
        rows.append(
            {
                "id": cid,
                "book_id": book_id,
                "locus": locus[:120],
                "text": text,
                "prev_id": f"{book_id}-{i:04d}" if i > 0 else None,
                "next_id": f"{book_id}-{i + 2:04d}" if i + 1 < len(items) else None,
                "char_count": len(text),
            }
        )
    return rows


def ingest_book(book_id: str, preferred: str | None = None) -> dict:
    book_dir = RAW / book_id
    if not book_dir.exists():
        return {"book_id": book_id, "ok": False, "error": "missing dir"}
    meta = load_meta(book_dir)
    status = str(meta.get("ingest_status", ""))
    if status in {"planned", "superseded"}:
        return {"book_id": book_id, "ok": False, "skipped": status}

    src = resolve_source(book_id, book_dir, preferred or meta.get("preferred_text"))
    if not src:
        return {"book_id": book_id, "ok": False, "error": "no txt"}

    text = src.read_text(encoding="utf-8", errors="replace")
    lang = meta.get("retrieval_language") or meta.get("language") or "zh"
    is_en = str(lang).startswith("en")
    min_c, max_c = SIZE.get(book_id) or (SIZE["default_en"] if is_en else SIZE["default_zh"])

    sections = split_sections(book_id, text)
    items: list[tuple[str, str]] = []
    for locus, sec in sections:
        items.extend(chunk_section(locus, sec, min_c, max_c))

    rows = link_ids(book_id, items)
    for r in rows:
        r["source_file"] = src.name
        r["retrieval_language"] = "en" if is_en else "zh"

    CHUNKS.mkdir(parents=True, exist_ok=True)
    out = CHUNKS / f"{book_id}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    chars = sum(r["char_count"] for r in rows)
    return {
        "book_id": book_id,
        "ok": True,
        "source": src.name,
        "chunks": len(rows),
        "chars": chars,
        "avg_chars": round(chars / len(rows), 1) if rows else 0,
        "out": str(out.relative_to(ROOT)) if ROOT in out.parents or out.parent == ROOT else str(out),
    }


def books_from_booklist(path: Path) -> list[tuple[str, str | None]]:
    if not path.exists():
        return []
    if yaml is None:
        raise SystemExit("PyYAML required for --booklist")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = []
    for b in data.get("books") or []:
        bid = b["book_id"]
        if b.get("ingest_status") == "superseded":
            continue
        out.append((bid, b.get("preferred_text")))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-root", type=Path, default=None)
    ap.add_argument("--booklist", type=Path, default=None)
    ap.add_argument("--only", default="", help="comma-separated book_id")
    args = ap.parse_args()
    c = bind(args.corpus_root)
    booklist = args.booklist or (c / "BOOKLIST.yaml")
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None

    books = books_from_booklist(booklist)
    if not books:
        # fallback: all raw dirs with META ready
        for d in sorted(RAW.iterdir()):
            if not d.is_dir():
                continue
            meta = load_meta(d)
            if meta.get("ingest_status") == "ready":
                books.append((d.name, meta.get("preferred_text")))

    results = []
    for bid, pref in books:
        if only and bid not in only:
            continue
        r = ingest_book(bid, pref)
        results.append(r)
        if r.get("ok"):
            print(
                f"OK {bid:22} chunks={r['chunks']:5} avg={r['avg_chars']:6} "
                f"→ {r['out']}"
            )
        else:
            print(f"SKIP {bid:22} {r}")

    summary = {
        "books_ok": sum(1 for r in results if r.get("ok")),
        "chunks_total": sum(r.get("chunks", 0) for r in results if r.get("ok")),
        "results": results,
    }
    summary_path = CHUNKS / "INGEST_SUMMARY.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {summary_path} books_ok={summary['books_ok']} chunks={summary['chunks_total']}")


if __name__ == "__main__":
    main()
