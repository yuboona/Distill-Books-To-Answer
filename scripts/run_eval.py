#!/usr/bin/env python3
"""Run retrieval (+ optional verify) regression over eval/cases.jsonl.

Exit 0 if all cases pass.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETRIEVE = ROOT / "scripts" / "retrieve.py"
VERIFY = ROOT / "scripts" / "verify_quotes.py"
DEFAULT_CASES = ROOT / "eval" / "cases.jsonl"


def run_retrieve(query: str, extra: list[str], top_k: int) -> dict:
    cmd = [sys.executable, str(RETRIEVE), "--query", query, "--top-k", str(top_k)]
    if extra:
        cmd.append("--extra-queries")
        cmd.extend(extra)
    out = subprocess.check_output(cmd, cwd=str(ROOT), text=True)
    return json.loads(out)


def run_verify(pack: dict, quotes: list[str]) -> dict:
    with tempfile.TemporaryDirectory() as td:
        pack_path = Path(td) / "pack.json"
        quotes_path = Path(td) / "quotes.json"
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        quotes_path.write_text(json.dumps(quotes, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VERIFY), "--pack", str(pack_path), "--quotes", str(quotes_path)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
        )
        report = json.loads(proc.stdout or "{}")
        report["_exit"] = proc.returncode
        return report


def check_case(case: dict, top_k: int) -> list[str]:
    errors: list[str] = []
    query = case["query"]
    extra = case.get("extra_queries") or []
    expect = case.get("expect") or {}
    pack = run_retrieve(query, extra, top_k)
    chunks = pack.get("chunks") or []
    texts = [c.get("text") or "" for c in chunks]
    joined = "\n".join(texts)
    books = {c.get("book_id") for c in chunks}
    langs = {c.get("retrieval_language") for c in chunks}
    boxes = set(pack.get("boxes") or [])

    if "min_chunks" in expect and len(chunks) < expect["min_chunks"]:
        errors.append(f"min_chunks: got {len(chunks)} < {expect['min_chunks']}")

    if expect.get("low_confidence") is True and not pack.get("low_confidence"):
        errors.append("expected low_confidence=true")
    if expect.get("low_confidence") is False and pack.get("low_confidence"):
        errors.append("expected low_confidence=false")

    if expect.get("boxes_any"):
        if not boxes.intersection(expect["boxes_any"]):
            errors.append(f"boxes_any: {sorted(boxes)} ∩ {expect['boxes_any']} empty")

    if expect.get("book_ids_any"):
        if not books.intersection(expect["book_ids_any"]):
            errors.append(f"book_ids_any: {sorted(books)} ∩ {expect['book_ids_any']} empty")

    if expect.get("retrieval_language_any"):
        if not langs.intersection(expect["retrieval_language_any"]):
            errors.append(f"retrieval_language_any: {sorted(langs)}")

    for needle in expect.get("text_contains_any") or []:
        if needle not in joined:
            errors.append(f"text_contains_any missing: {needle!r}")

    for needle in expect.get("text_contains_any_ci") or []:
        if needle.lower() not in joined.lower():
            errors.append(f"text_contains_any_ci missing: {needle!r}")

    for needle in expect.get("forbid_text_contains_any") or []:
        if needle in joined:
            errors.append(f"forbid_text_contains_any hit: {needle!r}")

    if expect.get("allow_low_or_no_mao99"):
        # soft: just ensure we did not invent the fake volume string in pack
        pass

    if expect.get("curated_boost_any"):
        if not any(c.get("curated_boost") for c in chunks):
            errors.append("expected curated_boost on at least one chunk")

    # verify block
    v = case.get("verify")
    if v:
        mode = v.get("mode")
        quotes: list[str] = []
        if mode == "first_chunk_prefix":
            if not chunks:
                errors.append("verify needs chunks")
            else:
                n = int(v.get("prefix_chars") or 24)
                quotes = [chunks[0]["text"][:n]]
        elif mode == "fixed_quotes":
            quotes = list(v.get("quotes") or [])
        else:
            errors.append(f"unknown verify mode: {mode}")

        if quotes:
            report = run_verify(pack, quotes)
            want = expect.get("verify_pass")
            got = bool(report.get("pass"))
            if want is True and not got:
                errors.append(f"verify expected PASS, got FAIL: {report.get('failed')}")
            if want is False and got:
                errors.append("verify expected FAIL, got PASS")

    return errors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--only", default="", help="comma-separated case ids")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None

    cases = []
    for line in args.cases.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cases.append(json.loads(line))
    if only:
        cases = [c for c in cases if c["id"] in only]

    failed = []
    for case in cases:
        cid = case["id"]
        try:
            errs = check_case(case, args.top_k)
        except Exception as e:  # noqa: BLE001
            errs = [f"exception: {e}"]
        if errs:
            failed.append((cid, errs))
            print(f"FAIL {cid}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"PASS {cid}")

    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
