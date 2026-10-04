#!/usr/bin/env python3
"""BOOKLIST-driven corpus fetch (meta-skill Mode BUILD, step B2–B3).

Dispatches each book's source.adapter:
  marxists_html / wikisource_html / gutenberg_txt / github_raw / local_path
  kanripo_volumes / git_markdown_anthology / plain_txt (aliases)

Heavy books may delegate to existing specialized scripts.

Usage:
  python3 scripts/fetch_from_booklist.py --status
  python3 scripts/fetch_from_booklist.py --only on_practice,sunzi
  python3 scripts/fetch_from_booklist.py --force --only the_prince
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.common import (  # noqa: E402
    TMP,
    bind as bind_corpus,
    decode_bytes,
    fetch_bytes,
    has_preferred_text,
    html_to_text,
    install_proxy_from_env,
    normalize,
    write_book,
)
from paths import default_booklist  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def load_booklist(path: Path) -> dict:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def meta_base(book: dict, source_url: str, edition: str, adapter: str) -> dict:
    return {
        "book_id": book["book_id"],
        "title": book.get("title", book["book_id"]),
        "title_en": book.get("title_en", ""),
        "box": book.get("box", "custom"),
        "language": book.get("language", "zh"),
        "retrieval_language": book.get("retrieval_language", "zh"),
        "answer_language": book.get("answer_language", "zh"),
        "license": book.get("license", "待填"),
        "edition_note": edition,
        "source_url": source_url,
        "source_adapter": adapter,
        "ingest_status": "ready",
        "preferred_text": book.get("preferred_text"),
    }


# ---------- adapters ----------


def adapt_marxists_html(book: dict, force: bool) -> str:
    src = book.get("source") or {}
    url = src.get("url")
    if not url:
        raise ValueError("marxists_html needs source.url")
    title = book.get("title") or book["book_id"]
    raw = decode_bytes(fetch_bytes(url))
    text = html_to_text(raw)
    idx = text.find(title[:2]) if title else -1
    # prefer exact title
    for key in (title, title[:4] if title else ""):
        if key and key in text:
            text = text[text.find(key) :]
            break
    for stop in ["马克思主义文库", "Marxists Internet Archive"]:
        j = text.rfind(stop)
        if j > len(text) * 0.6:
            text = text[:j]
    text = normalize(text)
    if len(text) < 500:
        raise RuntimeError(f"marxists body too short: {book['book_id']}")
    fname = book.get("preferred_text") or f"{book['book_id']}.txt"
    write_book(
        book["book_id"],
        fname,
        text,
        meta_base(book, url, "Marxists.org HTML cleaned", "marxists_html"),
    )
    return fname


def adapt_wikisource_html(book: dict, force: bool) -> str:
    src = book.get("source") or {}
    url = src.get("url") or ""
    # Prefer action=raw when MediaWiki page
    raw_url = src.get("raw_url")
    if not raw_url and "wikisource.org" in url and "action=raw" not in url:
        # convert /zh-hans/Title -> /wiki/Title?action=raw (best effort)
        raw_url = url.replace("/zh-hans/", "/wiki/").replace("/zh/", "/wiki/")
        if "action=raw" not in raw_url:
            raw_url = raw_url.split("?")[0] + "?action=raw"
    try_urls = [u for u in [raw_url, url] if u]
    body = ""
    used = try_urls[0]
    for u in try_urls:
        try:
            raw = decode_bytes(fetch_bytes(u))
        except Exception:
            continue
        if "<html" in raw[:200].lower():
            body = html_to_text(raw)
        else:
            body = raw
            body = __import__("re").sub(r"\{\{[^}]+\}\}", "", body)
            body = __import__("re").sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", body)
            body = __import__("re").sub(r"'{2,}", "", body)
            body = __import__("re").sub(r"<ref[^>]*>.*?</ref>", "", body, flags=__import__("re").S)
            body = __import__("re").sub(r"<[^>]+>", "", body)
        if len(body) > 200:
            used = u
            break
    text = normalize(body)
    if len(text) < 200:
        raise RuntimeError(f"wikisource body too short: {book['book_id']}")
    fname = book.get("preferred_text") or f"{book['book_id']}.txt"
    write_book(
        book["book_id"],
        fname,
        text,
        meta_base(book, used, "Wikisource cleaned", "wikisource_html"),
    )
    return fname


def adapt_gutenberg_txt(book: dict, force: bool) -> str:
    src = book.get("source") or {}
    raw_url = src.get("raw_url")
    gid = src.get("id")
    if not raw_url and gid:
        raw_url = f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt"
    if not raw_url:
        raise ValueError("gutenberg_txt needs source.raw_url or source.id")
    text = normalize(decode_bytes(fetch_bytes(raw_url)))
    # Trim PG header/footer lightly
    start_markers = ["*** START OF", "***START OF"]
    end_markers = ["*** END OF", "***END OF"]
    for m in start_markers:
        i = text.find(m)
        if i >= 0:
            nl = text.find("\n", i)
            text = text[nl + 1 :] if nl >= 0 else text[i:]
            break
    for m in end_markers:
        i = text.find(m)
        if i > 0:
            text = text[:i]
            break
    text = normalize(text)
    fname = book.get("preferred_text") or f"{book['book_id']}.txt"
    write_book(
        book["book_id"],
        fname,
        text,
        meta_base(book, raw_url, f"Project Gutenberg #{gid}", "gutenberg_txt"),
    )
    return fname


def adapt_github_raw(book: dict, force: bool) -> str:
    src = book.get("source") or {}
    raw_url = src.get("raw_url")
    if not raw_url:
        raise ValueError("github_raw/plain_txt needs source.raw_url")
    text = normalize(decode_bytes(fetch_bytes(raw_url)))
    if len(text) < 200:
        raise RuntimeError(f"github_raw too short: {book['book_id']}")
    fname = book.get("preferred_text") or f"{book['book_id']}.txt"
    write_book(
        book["book_id"],
        fname,
        text,
        meta_base(book, raw_url, "GitHub raw text", src.get("adapter") or "github_raw"),
    )
    return fname


def adapt_local_path(book: dict, force: bool) -> str:
    src = book.get("source") or {}
    path = Path(src.get("path") or "").expanduser()
    if not path.exists():
        raise FileNotFoundError(path)
    text = normalize(path.read_text(encoding="utf-8", errors="replace"))
    fname = book.get("preferred_text") or path.name
    write_book(
        book["book_id"],
        fname,
        text,
        meta_base(book, str(path), "local_path import", "local_path"),
    )
    return fname


def adapt_kanripo_volumes(book: dict, force: bool) -> str:
    """Download KR*.txt volumes from a kanripo GitHub repo and concatenate."""
    import re

    src = book.get("source") or {}
    repo = (src.get("url") or "").rstrip("/")
    # https://github.com/kanripo/KR3a0006 -> raw base
    m = re.search(r"github.com/([^/]+)/([^/]+)", repo)
    if not m:
        raise ValueError("kanripo_volumes needs github url")
    owner, name = m.group(1), m.group(2)
    prefix = src.get("file_prefix") or name  # e.g. KR3a0006
    start = int(src.get("vol_start") or 1)
    end = int(src.get("vol_end") or 12)
    parts = [f"{book.get('title', book['book_id'])}\n来源: {repo}\n"]
    cache = TMP / f"kanripo_{prefix}"
    cache.mkdir(parents=True, exist_ok=True)
    for i in range(start, end + 1):
        fname = f"{prefix}_{i:03d}.txt"
        url = f"https://raw.githubusercontent.com/{owner}/{name}/master/{fname}"
        cpath = cache / fname
        if force or not cpath.exists():
            cpath.write_bytes(fetch_bytes(url))
        t = cpath.read_text(encoding="utf-8", errors="replace")
        lines = []
        for ln in t.splitlines():
            if ln.startswith("#+") or ln.startswith("# -*-"):
                continue
            ln = re.sub(r"<pb:[^>]+>", "", ln).replace("¶", "")
            lines.append(ln)
        parts.append(f"\n\n===== 卷{i:03d} =====\n\n" + "\n".join(lines).strip() + "\n")
    text = normalize("".join(parts))
    out_name = book.get("preferred_text") or f"{book['book_id']}.txt"
    write_book(
        book["book_id"],
        out_name,
        text,
        meta_base(book, repo, f"kanripo {prefix} vols {start}-{end}", "kanripo_volumes"),
    )
    return out_name


def adapt_git_markdown_anthology(book: dict, force: bool) -> str:
    """Delegate Mao anthology (and similar) to specialized script."""
    script = ROOT / "scripts" / "fetch_mao_selected_works.py"
    if book["book_id"] != "mao_selected_works":
        raise ValueError("git_markdown_anthology currently wired for mao_selected_works only")
    cmd = [sys.executable, str(script)]
    if (book.get("source") or {}).get("with_jinghuo"):
        cmd.append("--with-jinghuo")
    # always allow jinghuo flag via booklist note default on
    if "--with-jinghuo" not in cmd:
        cmd.append("--with-jinghuo")
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    return book.get("preferred_text") or "毛泽东选集_1-5卷.txt"


def adapt_delegate_tongjian(book: dict, force: bool) -> str:
    script = ROOT / "scripts" / "fetch_tongjian_loop.sh"
    if not script.exists():
        raise FileNotFoundError(script)
    # Prefer existing full text; only run loop if missing
    pref = book.get("preferred_text") or "资治通鉴_全文.txt"
    target = ROOT / "corpus" / "raw" / book["book_id"] / pref
    if target.exists() and not force:
        return pref
    env = dict(**__import__("os").environ)
    subprocess.run(["bash", str(script)], cwd=str(ROOT), check=True, env=env)
    if not target.exists():
        raise RuntimeError("tongjian fetch finished but preferred_text missing; check loop script output")
    return pref


ADAPTERS = {
    "marxists_html": adapt_marxists_html,
    "wikisource_html": adapt_wikisource_html,
    "gutenberg_txt": adapt_gutenberg_txt,
    "github_raw": adapt_github_raw,
    "plain_txt": adapt_github_raw,  # alias: expects raw_url
    "local_path": adapt_local_path,
    "kanripo_volumes": adapt_kanripo_volumes,
    "git_markdown_anthology": adapt_git_markdown_anthology,
    "tongjian_loop": adapt_delegate_tongjian,
}


def fetch_one(book: dict, force: bool, dry_run: bool) -> dict:
    bid = book["book_id"]
    status = book.get("ingest_status")
    src = book.get("source") or {}
    adapter = src.get("adapter") or ""
    if status == "superseded":
        return {
            "book_id": bid,
            "ok": dry_run,
            "skipped": "superseded",
            "dry_run": adapter if dry_run else None,
        }
    if dry_run:
        return {
            "book_id": bid,
            "ok": True,
            "dry_run": adapter,
            "has_text": has_preferred_text(book),
        }
    if not force and has_preferred_text(book) and status == "ready":
        return {"book_id": bid, "ok": True, "skipped": "already_has_text"}
    if adapter not in ADAPTERS:
        return {"book_id": bid, "ok": False, "error": f"unknown adapter: {adapter}"}
    try:
        out = ADAPTERS[adapter](book, force)
        return {"book_id": bid, "ok": True, "file": out, "adapter": adapter}
    except Exception as e:  # noqa: BLE001
        return {"book_id": bid, "ok": False, "error": str(e), "adapter": adapter}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch corpus texts from BOOKLIST.yaml")
    ap.add_argument("--corpus-root", type=Path, default=None)
    ap.add_argument("--booklist", type=Path, default=None)
    ap.add_argument("--only", default="", help="comma-separated book_id")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true", help="show adapter plan only")
    args = ap.parse_args()
    c = bind_corpus(args.corpus_root)
    if args.booklist is None:
        args.booklist = default_booklist(c)
    proxy = install_proxy_from_env()
    print(f"proxy={proxy or '(none)'}")

    data = load_booklist(args.booklist)
    books = data.get("books") or []
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None

    if args.status or args.dry_run:
        print(f"{'book_id':22} {'status':12} {'adapter':24} text")
        for b in books:
            if only and b["book_id"] not in only:
                continue
            src = b.get("source") or {}
            print(
                f"{b['book_id']:22} {str(b.get('ingest_status')):12} "
                f"{str(src.get('adapter')):24} "
                f"{'yes' if has_preferred_text(b) else 'no'}"
            )
        if args.status and not args.dry_run:
            return

    results = []
    for b in books:
        if only and b["book_id"] not in only:
            continue
        r = fetch_one(b, force=args.force, dry_run=args.dry_run)
        results.append(r)
        if r.get("skipped"):
            print(f"SKIP {r['book_id']}: {r['skipped']}")
        elif r.get("ok"):
            print(f"OK   {r['book_id']}: {r.get('file') or r.get('dry_run')}")
        else:
            print(f"FAIL {r['book_id']}: {r.get('error')}")

    ok = sum(1 for r in results if r.get("ok"))
    hard_fail = sum(1 for r in results if r.get("error"))
    print(f"done ok={ok}/{len(results)} hard_fail={hard_fail}")
    raise SystemExit(1 if hard_fail else 0)


if __name__ == "__main__":
    main()
