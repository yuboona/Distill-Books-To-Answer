#!/usr/bin/env python3
"""Resolve corpus/project roots for meta-skill BUILD + COUNSEL.

Scripts may live in the workspace (`05-shi-shi-qiu-shi/`) or in the
distributed skill package. Corpus text never lives inside the skill pack.

Precedence for corpus root:
  1. explicit override (--corpus-root)
  2. env SSQS_CORPUS_ROOT
  3. ./corpus or ./05-shi-shi-qiu-shi/corpus if they look like a corpus
  4. <package>/corpus (empty skeleton in the skill pack)
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def corpus_root(override: Path | str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("SSQS_CORPUS_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    cwd = Path.cwd()
    for cand in (cwd / "corpus", cwd / "05-shi-shi-qiu-shi" / "corpus"):
        if (cand / "BOOKLIST.yaml").exists() or (cand / "raw").exists() or (cand / "chunks").exists():
            return cand.resolve()
    return (PACKAGE_ROOT / "corpus").resolve()


def project_root(corpus: Path | None = None) -> Path:
    return (corpus or corpus_root()).parent


def raw_dir(corpus: Path | None = None) -> Path:
    return (corpus or corpus_root()) / "raw"


def chunks_dir(corpus: Path | None = None) -> Path:
    return (corpus or corpus_root()) / "chunks"


def quotes_path(corpus: Path | None = None) -> Path:
    return (corpus or corpus_root()) / "quotes" / "curated.jsonl"


def default_booklist(corpus: Path | None = None) -> Path:
    return (corpus or corpus_root()) / "BOOKLIST.yaml"


def download_tmp(corpus: Path | None = None) -> Path:
    return project_root(corpus) / ".download_tmp"
