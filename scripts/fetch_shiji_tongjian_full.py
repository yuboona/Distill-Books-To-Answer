#!/usr/bin/env python3
"""Download full 史记 + 资治通鉴 into corpus/raw (full text, not selections)."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
TMP = ROOT / ".download_tmp"
UA = "shi-shi-qiu-shi-corpus/0.2 (personal research)"
DEFAULT_PROXY = "http://127.0.0.1:7890"


def setup_proxy(proxy: str | None) -> str | None:
    for k in list(os.environ):
        if "proxy" in k.lower():
            os.environ.pop(k, None)
    if not proxy:
        print("proxy: disabled")
        return None
    os.environ["http_proxy"] = proxy
    os.environ["https_proxy"] = proxy
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    print(f"proxy: {proxy}")
    return proxy


def fetch(url: str, dest: Path, proxy: str | None, retries: int = 8) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with opener.open(req, timeout=180) as resp:
                data = resp.read()
            if len(data) < 1000:
                raise RuntimeError(f"too small ({len(data)} bytes)")
            partial.write_bytes(data)
            partial.replace(dest)
            print(f"  OK {dest.name} ({len(data)} bytes) attempt={attempt}")
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  fail attempt {attempt}: {e}")
            time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"failed {url}: {last_err}")


def meta_yaml(meta: dict) -> str:
    lines = []
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def install_shiji(proxy: str | None) -> None:
    mirrors = [
        "https://raw.githubusercontent.com/baojie/shiji-kb/main/corpus/shiji/%E5%8F%B2%E8%AE%B0.%E7%AE%80%E4%BD%93.txt",
        "https://cdn.jsdelivr.net/gh/baojie/shiji-kb@main/corpus/shiji/%E5%8F%B2%E8%AE%B0.%E7%AE%80%E4%BD%93.txt",
    ]
    dest = TMP / "史记.简体.txt"
    ok = False
    for u in mirrors:
        print(f"== shiji {u}")
        try:
            fetch(u, dest, proxy=proxy)
            ok = True
            break
        except Exception as e:  # noqa: BLE001
            print(f"  mirror failed: {e}")
    if not ok:
        raise RuntimeError("all shiji mirrors failed")

    text = normalize(dest.read_text(encoding="utf-8", errors="replace"))
    # Expect roughly full book size
    if len(text) < 400_000:
        raise RuntimeError(f"shiji text unexpectedly small: {len(text)} chars")

    out_dir = RAW / "shiji"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "史记.简体.txt").write_text(text, encoding="utf-8")
    (out_dir / "META.yaml").write_text(
        meta_yaml(
            {
                "book_id": "shiji",
                "title": "史记",
                "title_en": "Records of the Grand Historian",
                "box": "history",
                "language": "zh",
                "coverage": "full",
                "edition_note": "baojie/shiji-kb 史记.简体.txt full text",
                "source_url": "https://github.com/baojie/shiji-kb/tree/main/corpus/shiji",
                "license": "classical public-domain text via public corpus; personal research",
                "ingest_status": "ready",
                "answer_language": "zh",
                "retrieval_language": "zh",
                "char_count": len(text),
            }
        ),
        encoding="utf-8",
    )
    print(f"installed shiji chars={len(text)}")


def install_tongjian(proxy: str | None) -> None:
    out_dir = RAW / "zizhi_tongjian" / "volumes"
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = [
        "https://raw.githubusercontent.com/kanripo/KR2b0007/master/KR2b0007_{:03d}.txt",
        "https://cdn.jsdelivr.net/gh/kanripo/KR2b0007@master/KR2b0007_{:03d}.txt",
    ]
    failed: list[int] = []
    for i in range(0, 295):
        dest = out_dir / f"卷{i:03d}.txt"
        if dest.exists() and dest.stat().st_size > 500:
            print(f"  skip {dest.name}")
            continue
        ok = False
        for tmpl in templates:
            url = tmpl.format(i)
            print(f"== tongjian {i:03d}")
            try:
                fetch(url, dest, proxy=proxy, retries=5)
                text = normalize(dest.read_text(encoding="utf-8", errors="replace"))
                dest.write_text(text, encoding="utf-8")
                ok = True
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {e}")
        if not ok:
            failed.append(i)

    parts: list[str] = []
    present = 0
    for i in range(0, 295):
        p = out_dir / f"卷{i:03d}.txt"
        if not p.exists():
            continue
        present += 1
        parts.append(f"\n\n===== 卷{i:03d} =====\n\n")
        parts.append(p.read_text(encoding="utf-8"))
    master = RAW / "zizhi_tongjian" / "资治通鉴_全文.txt"
    master.write_text("".join(parts), encoding="utf-8")

    status = "ready" if not failed and present >= 290 else "partial"
    (RAW / "zizhi_tongjian" / "META.yaml").write_text(
        meta_yaml(
            {
                "book_id": "zizhi_tongjian",
                "title": "资治通鉴",
                "title_en": "Zizhi Tongjian",
                "box": "history",
                "language": "classical_zh",
                "coverage": "full",
                "edition_note": "kanripo/KR2b0007 volumes 000-294 concatenated",
                "source_url": "https://github.com/kanripo/KR2b0007",
                "license": "classical text via Kanseki Repository; personal research",
                "ingest_status": status,
                "answer_language": "zh",
                "retrieval_language": "zh",
                "volumes_present": present,
                "failed_volumes": failed,
                "bytes": master.stat().st_size,
            }
        ),
        encoding="utf-8",
    )
    print(f"tongjian present={present}/295 failed={failed} bytes={master.stat().st_size}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--proxy",
        default=DEFAULT_PROXY,
        help="HTTP proxy, default http://127.0.0.1:7890; pass empty to disable",
    )
    ap.add_argument("--no-proxy", action="store_true")
    ap.add_argument("--only", choices=["shiji", "tongjian", "all"], default="all")
    args = ap.parse_args()
    proxy = None if args.no_proxy else (args.proxy or None)
    proxy = setup_proxy(proxy)
    TMP.mkdir(parents=True, exist_ok=True)
    if args.only in ("shiji", "all"):
        install_shiji(proxy)
    if args.only in ("tongjian", "all"):
        install_tongjian(proxy)


if __name__ == "__main__":
    main()
