#!/usr/bin/env python3
"""Cold-start acceptance (docs/13 §8). Does not touch the instance corpus.

1. Empty corpus → retrieve returns 0 chunks (COUNSEL must stay L0).
2. Fresh temp corpus + 2-book BOOKLIST → fetch → ingest → retrieve hits.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
INSTANCE = PKG / "corpus"
EXAMPLE = PKG / "templates" / "BOOKLIST.example.yaml"


def run(cmd: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(PKG), env=env, text=True, capture_output=True)


def fail(msg: str, proc: subprocess.CompletedProcess | None = None) -> None:
    print(f"FAIL {msg}", file=sys.stderr)
    if proc is not None:
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
    raise SystemExit(1)


def retrieve(corpus: Path, query: str, out: Path) -> dict:
    env = os.environ.copy()
    env["SSQS_CORPUS_ROOT"] = str(corpus)
    proc = run(
        [
            sys.executable,
            str(HERE / "retrieve.py"),
            "--corpus-root",
            str(corpus),
            "--query",
            query,
            "--out",
            str(out),
        ],
        env=env,
    )
    if proc.returncode != 0:
        fail(f"retrieve {query!r}", proc)
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> None:
    before_chunks = sorted(p.name for p in (INSTANCE / "chunks").glob("*.jsonl")) if (INSTANCE / "chunks").exists() else []

    empty = Path(tempfile.mkdtemp(prefix="ssqs-empty-"))
    try:
        pack = retrieve(empty, "司马光 资治通鉴 玄武门", empty / "pack.json")
        books = {c.get("book_id") for c in pack.get("chunks") or []}
        if pack.get("chunks"):
            fail(f"empty corpus must return 0 chunks, got {books}")
        if "zizhi_tongjian" in books or "shiji" in books:
            fail(f"empty corpus leaked instance books: {books}")
        print("OK empty-corpus L0 (0 chunks, no 通鉴/史记 leak)")
    finally:
        shutil.rmtree(empty, ignore_errors=True)

    tmp = Path(tempfile.mkdtemp(prefix="ssqs-cold-"))
    corpus = tmp / "corpus"
    corpus.mkdir(parents=True)
    booklist = corpus / "BOOKLIST.yaml"
    shutil.copyfile(EXAMPLE, booklist)
    env = os.environ.copy()
    env["SSQS_CORPUS_ROOT"] = str(corpus)
    if not env.get("https_proxy") and not env.get("HTTPS_PROXY"):
        env["https_proxy"] = "http://127.0.0.1:7890"
        env["http_proxy"] = "http://127.0.0.1:7890"

    src_practice = INSTANCE / "raw" / "on_practice" / "实践论.txt"
    src_sunzi = INSTANCE / "raw" / "sunzi" / "孙子兵法.txt"

    def write_local_booklist() -> None:
        if not src_practice.exists() or not src_sunzi.exists():
            fail("instance raw texts missing; cannot fallback to local_path")
        booklist.write_text(
            f"""corpus_root: corpus
books:
  - book_id: on_practice
    title: 实践论
    box: epistemology
    language: zh
    retrieval_language: zh
    ingest_status: planned
    preferred_text: 实践论.txt
    source:
      adapter: local_path
      path: {src_practice}
  - book_id: sunzi
    title: 孙子兵法
    box: strategy
    language: classical_zh
    retrieval_language: zh
    ingest_status: planned
    preferred_text: 孙子兵法.txt
    source:
      adapter: local_path
      path: {src_sunzi}
""",
            encoding="utf-8",
        )

    try:
        boot = run(
            [
                sys.executable,
                str(HERE / "bootstrap_corpus.py"),
                "--booklist",
                str(booklist),
                "--corpus-root",
                str(corpus),
            ],
            env=env,
        )
        if boot.returncode != 0:
            fail("bootstrap", boot)

        fetch = run(
            [
                sys.executable,
                str(HERE / "fetch_from_booklist.py"),
                "--booklist",
                str(booklist),
                "--corpus-root",
                str(corpus),
                "--only",
                "on_practice,sunzi",
            ],
            env=env,
        )
        print(fetch.stdout)
        if fetch.returncode != 0:
            print("WARN network fetch failed; falling back to local_path (docs/13 §8.2)")
            write_local_booklist()
            fetch = run(
                [
                    sys.executable,
                    str(HERE / "fetch_from_booklist.py"),
                    "--booklist",
                    str(booklist),
                    "--corpus-root",
                    str(corpus),
                    "--only",
                    "on_practice,sunzi",
                    "--force",
                ],
                env=env,
            )
            print(fetch.stdout)
            if fetch.returncode != 0:
                fail("fetch local_path", fetch)

        ingest = run(
            [
                sys.executable,
                str(HERE / "ingest.py"),
                "--booklist",
                str(booklist),
                "--corpus-root",
                str(corpus),
                "--only",
                "on_practice,sunzi",
            ],
            env=env,
        )
        print(ingest.stdout)
        if ingest.returncode != 0:
            fail("ingest", ingest)

        p1 = retrieve(corpus, "通过实践而发现真理", tmp / "p1.json")
        p1_books = {c.get("book_id") for c in p1.get("chunks") or []}
        if "on_practice" not in p1_books:
            fail(f"practice retrieve missed on_practice: {p1_books} n={len(p1.get('chunks') or [])}")
        if "zizhi_tongjian" in p1_books:
            fail("cold corpus retrieved 通鉴 from instance")

        p2 = retrieve(corpus, "知彼知己", tmp / "p2.json")
        p2_books = {c.get("book_id") for c in p2.get("chunks") or []}
        if "sunzi" not in p2_books:
            fail(f"sunzi retrieve missed sunzi: {p2_books}")

        quote = None
        for c in p1["chunks"]:
            if c.get("book_id") == "on_practice" and "实践" in c.get("text", ""):
                # shortest verifiable span
                text = c["text"]
                i = text.find("实践")
                quote = text[max(0, i) : i + 8]
                break
        if not quote:
            fail("no 实践 span in pack")
        ver = run(
            [
                sys.executable,
                str(HERE / "verify_quotes.py"),
                "--pack",
                str(tmp / "p1.json"),
                "--quote",
                quote,
            ],
            env=env,
        )
        print(ver.stdout)
        if ver.returncode != 0:
            fail("verify", ver)

        print("OK cold-start BUILD: on_practice + sunzi ingest/retrieve/verify")
        print(f"    corpus={corpus}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    after_chunks = sorted(p.name for p in (INSTANCE / "chunks").glob("*.jsonl")) if (INSTANCE / "chunks").exists() else []
    if after_chunks != before_chunks:
        fail(f"instance chunks changed: {before_chunks} → {after_chunks}")
    print(f"OK instance corpus untouched ({len(after_chunks)} chunk files)")
    print("COLDSTART PASS")


if __name__ == "__main__":
    main()
