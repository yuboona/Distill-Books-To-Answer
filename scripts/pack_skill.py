#!/usr/bin/env python3
"""Copy protocol + scripts into the personal skill pack. Never copies book texts."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
DEFAULT_DEST = Path.home() / ".cursor" / "skills" / "shi-shi-qiu-shi"

SKIP_DIR_NAMES = {"__pycache__", ".download_tmp", ".git"}
SKIP_SUFFIXES = {".pyc"}


def copy_tree(src: Path, dest: Path) -> int:
    n = 0
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in p.parts):
            continue
        if p.suffix in SKIP_SUFFIXES:
            continue
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = ap.parse_args()
    dest = args.dest.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    counts = {
        "scripts": copy_tree(PKG / "scripts", dest / "scripts"),
        "docs": copy_tree(PKG / "docs", dest / "docs"),
        "templates": copy_tree(PKG / "templates", dest / "templates"),
        "eval/smoke": copy_tree(PKG / "eval" / "smoke", dest / "eval" / "smoke"),
    }
    if (PKG / "scripts" / "README.md").exists():
        shutil.copy2(PKG / "scripts" / "README.md", dest / "scripts" / "README.md")

    corpus = dest / "corpus"
    corpus.mkdir(exist_ok=True)
    (corpus / "README.md").write_text(
        "# corpus（本地产物，不随 skill 分发正文）\n\n"
        "把 `templates/BOOKLIST.example.yaml` 复制为 `BOOKLIST.yaml` 后跑 BUILD。\n"
        "检索默认看 `SSQS_CORPUS_ROOT`，或工作区 `05-shi-shi-qiu-shi/corpus`，或本目录。\n",
        encoding="utf-8",
    )
    (corpus / ".gitkeep").write_text("", encoding="utf-8")
    (corpus / ".gitignore").write_text(
        "raw/**/*.txt\nchunks/*.jsonl\nquotes/*.jsonl\n!quotes/README.md\n.download_tmp/\n",
        encoding="utf-8",
    )

    print(f"packed → {dest}")
    for k, v in counts.items():
        print(f"  {k}: {v} files")
    if not (dest / "SKILL.md").exists():
        print("WARN missing SKILL.md (not overwritten; create in dest first)", file=sys.stderr)


if __name__ == "__main__":
    main()
