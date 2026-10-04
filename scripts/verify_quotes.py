#!/usr/bin/env python3
"""Verify that quoted strings are exact substrings of Context Pack / chunks.

No script-fold, no translation. See docs/06-verification.md and docs/12.

Usage:
  python3 scripts/verify_quotes.py --pack pack.json --quotes quotes.json
  python3 scripts/verify_quotes.py --pack pack.json --quote '...' --quote '...'
  echo '["quote1","quote2"]' | python3 scripts/verify_quotes.py --pack pack.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_pack(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_corpus(pack: dict) -> list[tuple[str, str, str]]:
    """Return (chunk_id, book_id, text) from pack."""
    out = []
    for c in pack.get("chunks") or []:
        out.append((c.get("id", ""), c.get("book_id", ""), c.get("text", "")))
    return out


def verify_one(quote: str, corpus: list[tuple[str, str, str]]) -> dict:
    q = quote.strip()
    if not q:
        return {"quote": quote, "ok": False, "reason": "empty"}
    for cid, book_id, text in corpus:
        if q in text:
            return {
                "quote": q,
                "ok": True,
                "chunk_id": cid,
                "book_id": book_id,
                "char_count": len(q),
            }
    return {
        "quote": q,
        "ok": False,
        "reason": "not_a_substring_of_pack",
        "hint": "Do not fold trad/simp or translate before verify",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True, help="Context Pack JSON from retrieve.py")
    ap.add_argument("--quote", action="append", default=[], help="Quote string (repeatable)")
    ap.add_argument("--quotes", default="", help="JSON file: list of strings or {quotes:[...]}")
    ap.add_argument("--out", default="", help="Write report JSON")
    args = ap.parse_args()

    pack = load_pack(Path(args.pack))
    corpus = collect_corpus(pack)
    quotes: list[str] = list(args.quote)

    if args.quotes:
        data = json.loads(Path(args.quotes).read_text(encoding="utf-8"))
        if isinstance(data, list):
            quotes.extend(str(x) for x in data)
        elif isinstance(data, dict):
            quotes.extend(str(x) for x in data.get("quotes") or [])

    if not quotes and not sys.stdin.isatty():
        data = json.load(sys.stdin)
        if isinstance(data, list):
            quotes.extend(str(x) for x in data)

    if not quotes:
        print("No quotes provided", file=sys.stderr)
        raise SystemExit(2)

    results = [verify_one(q, corpus) for q in quotes]
    report = {
        "pack_query": pack.get("query"),
        "pack_chunks": len(corpus),
        "results": results,
        "pass": all(r["ok"] for r in results),
        "failed": [r for r in results if not r["ok"]],
    }
    s = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(s, encoding="utf-8")
        print(f"wrote {args.out} pass={report['pass']} failed={len(report['failed'])}")
    else:
        print(s)
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
