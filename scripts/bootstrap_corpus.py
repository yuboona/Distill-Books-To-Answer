#!/usr/bin/env python3
"""Bootstrap corpus skeleton from BOOKLIST.yaml (meta-skill Mode BUILD, step B0–B1).

Creates corpus/raw/<book_id>/META.yaml for each book. Does NOT fetch full text.
Existing META.yaml is left untouched unless --force.

Usage:
  python3 scripts/bootstrap_corpus.py
  python3 scripts/bootstrap_corpus.py --booklist corpus/BOOKLIST.yaml --status
  python3 scripts/bootstrap_corpus.py --only yan_tie_lun,chuanxilu
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import PACKAGE_ROOT, corpus_root, default_booklist  # noqa: E402

ROOT = PACKAGE_ROOT

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def load_booklist(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    # Minimal fallback: require PyYAML for nested structures
    raise SystemExit(
        "PyYAML required: pip install pyyaml\n"
        f"(tried to load {path})"
    )


def meta_from_book(book: dict, defaults: dict) -> dict:
    src = book.get("source") or {}
    meta = {
        "book_id": book["book_id"],
        "title": book.get("title", book["book_id"]),
        "title_en": book.get("title_en", ""),
        "box": book.get("box", "custom"),
        "language": book.get("language", "zh"),
        "edition_note": book.get("edition_note", "bootstrap skeleton; fill after fetch"),
        "source_url": src.get("url", ""),
        "license": book.get("license", "待填"),
        "ingest_status": book.get("ingest_status", "planned"),
        "answer_language": book.get("answer_language", defaults.get("answer_language", "zh")),
        "retrieval_language": book.get("retrieval_language", "zh"),
    }
    if book.get("preferred_text"):
        meta["preferred_text"] = book["preferred_text"]
    if book.get("coverage"):
        meta["coverage"] = book["coverage"]
    if book.get("retrieval_note"):
        meta["retrieval_note"] = book["retrieval_note"]
    if src.get("adapter"):
        meta["source_adapter"] = src["adapter"]
    if src.get("type"):
        meta["source_type"] = src["type"]
    return meta


def dump_meta(meta: dict) -> str:
    if yaml is not None:
        return yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
    # unlikely path
    return json.dumps(meta, ensure_ascii=False, indent=2)


def text_present(raw_dir: Path, preferred: str | None) -> bool:
    if preferred and (raw_dir / preferred).exists():
        return True
    return any(raw_dir.glob("*.txt"))


def bootstrap(
    booklist_path: Path,
    corpus_root: Path | None,
    only: set[str] | None,
    force: bool,
    status_only: bool,
) -> int:
    data = load_booklist(booklist_path)
    defaults = data.get("defaults") or {}
    books = data.get("books") or []
    root = corpus_root or (ROOT / (data.get("corpus_root") or "corpus"))
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (root / "chunks").mkdir(parents=True, exist_ok=True)
    (root / "quotes").mkdir(parents=True, exist_ok=True)

    def row_for(book: dict) -> dict:
        bid = book["book_id"]
        bdir = raw / bid
        preferred = book.get("preferred_text")
        has_text = text_present(bdir, preferred) if bdir.exists() else False
        listed_status = book.get("ingest_status", "planned")
        effective = listed_status
        if listed_status == "ready" and not has_text:
            effective = "planned (BOOKLIST says ready but no .txt)"
        elif has_text and listed_status == "planned":
            effective = "partial (text present, BOOKLIST still planned)"
        return {
            "book_id": bid,
            "box": book.get("box"),
            "listed": listed_status,
            "effective": effective,
            "has_text": has_text,
            "meta_exists": (bdir / "META.yaml").exists(),
            "adapter": (book.get("source") or {}).get("adapter"),
        }

    # Full status always (even when --only filters writes)
    all_rows = [row_for(b) for b in books]
    write_books = [b for b in books if not only or b["book_id"] in only]
    rows = [row_for(b) for b in write_books]

    created = updated = skipped = 0
    for book in write_books:
        bid = book["book_id"]
        bdir = raw / bid
        bdir.mkdir(parents=True, exist_ok=True)
        meta_path = bdir / "META.yaml"
        if status_only:
            continue
        meta = meta_from_book(book, defaults)
        existed = meta_path.exists()
        if existed and not force:
            skipped += 1
            continue
        meta_path.write_text(dump_meta(meta), encoding="utf-8")
        if existed:
            updated += 1
        else:
            created += 1

    status_path = root / "BOOKLIST.status.json"
    payload = {
        "booklist": str(booklist_path),
        "corpus_root": str(root),
        "books": all_rows,
        "ready_with_text": sum(
            1 for r in all_rows if r["has_text"] and r["listed"] == "ready"
        ),
        "planned": sum(1 for r in all_rows if r["listed"] == "planned"),
    }
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"booklist: {booklist_path}")
    print(f"corpus:   {root}")
    print(f"{'book_id':22} {'listed':8} {'text':5} {'adapter':22} effective")
    for r in rows:
        print(
            f"{r['book_id']:22} {r['listed']:8} "
            f"{'yes' if r['has_text'] else 'no':5} "
            f"{(r['adapter'] or '-'):22} {r['effective']}"
        )
    if not status_only:
        print(f"META created={created}, updated={updated}, skipped_existing={skipped}")
    print(f"wrote {status_path} (full list: {len(all_rows)} books, ready_with_text={payload['ready_with_text']})")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Bootstrap corpus dirs from BOOKLIST.yaml")
    ap.add_argument(
        "--booklist",
        type=Path,
        default=None,
        help="Path to BOOKLIST.yaml",
    )
    ap.add_argument(
        "--corpus-root",
        type=Path,
        default=None,
        help="Override corpus root (default: from booklist or ./corpus)",
    )
    ap.add_argument("--only", default="", help="Comma-separated book_id filter")
    ap.add_argument("--force", action="store_true", help="Overwrite existing META.yaml")
    ap.add_argument("--status", action="store_true", help="Report only; do not write META")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    booklist = args.booklist or default_booklist(args.corpus_root)
    raise SystemExit(
        bootstrap(booklist, args.corpus_root, only, args.force, args.status)
    )


if __name__ == "__main__":
    main()
