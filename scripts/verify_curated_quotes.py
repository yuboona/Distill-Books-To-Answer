#!/usr/bin/env python3
"""Validate curated quotes are exact substrings of their chunk_id texts.

Exit 0 if all quotes verify against corpus/chunks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "corpus" / "chunks"
QUOTES = ROOT / "corpus" / "quotes" / "curated.jsonl"


def load_chunk(book_id: str, chunk_id: str) -> str | None:
    path = CHUNKS / f"{book_id}.jsonl"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") == chunk_id:
            return row.get("text") or ""
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quotes", type=Path, default=QUOTES)
    args = ap.parse_args()
    failed = []
    n = 0
    for line in args.quotes.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n += 1
        row = json.loads(line)
        qid = row.get("id")
        quote = row.get("quote") or ""
        book_id = row.get("book_id")
        chunk_id = row.get("chunk_id")
        text = load_chunk(book_id, chunk_id)
        if text is None:
            failed.append((qid, "chunk_not_found", chunk_id))
            continue
        if quote not in text:
            failed.append((qid, "not_substring", chunk_id))
            continue
        print(f"PASS {qid}")
    if failed:
        for item in failed:
            print("FAIL", item)
        print(f"{n - len(failed)}/{n} passed")
        raise SystemExit(1)
    print(f"{n}/{n} passed")


if __name__ == "__main__":
    main()
