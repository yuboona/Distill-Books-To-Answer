#!/usr/bin/env python3
"""Fetch full 《毛泽东选集》 (official vols 1–5) into corpus/raw/mao_selected_works.

Source: NpTIme/MaoZeDongAnthology (Markdown of official edition).
Uses HTTPS_PROXY / http_proxy if set (e.g. http://127.0.0.1:7890).

Optional --with-jinghuo also packs unofficial vols 6–7 into a separate file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw" / "mao_selected_works"
TMP = ROOT / ".download_tmp" / "MaoZeDongAnthology"
REPO = "https://github.com/NpTIme/MaoZeDongAnthology.git"

OFFICIAL_DIRS = [
    ("01", "001-第一卷 国内革命战争时期", "第一卷"),
    ("02", "002-第二卷 抗日战争时期（上）", "第二卷"),
    ("03", "003-第三卷 抗日战争时期（下）", "第三卷"),
    ("04", "004-第四卷 第三次国内革命战争时期", "第四卷"),
    ("05", "005-第五卷 社会主义革命和社会主义建设时期（一）", "第五卷"),
]

UNOFFICIAL_DIRS = [
    ("06", "006-第六卷 社会主义革命和社会主义建设时期（二）【非官方版本】", "第六卷（静火非官方）"),
    ("07", "007-第七卷 文化大革命时期【非官方版本】", "第七卷（静火非官方）"),
]


def ensure_clone() -> None:
    if (TMP / "README.md").exists():
        print(f"using existing clone: {TMP}")
        return
    TMP.parent.mkdir(parents=True, exist_ok=True)
    if TMP.exists():
        # incomplete
        subprocess.run(["rm", "-rf", str(TMP)], check=False)
    env = os.environ.copy()
    cmd = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "clone",
        "--depth",
        "1",
        REPO,
        str(TMP),
    ]
    print("cloning", REPO)
    subprocess.run(cmd, check=True, env=env)


def strip_md(text: str) -> str:
    # light markdown → plain for retrieval
    text = text.replace("\r\n", "\n")
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)  # front matter
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def collect_volume(dirname: str, vol_label: str) -> tuple[str, int]:
    root = TMP / dirname
    files = sorted(root.rglob("*.md"))
    parts: list[str] = [f"\n\n{'=' * 72}\n{vol_label}\n{'=' * 72}\n"]
    n = 0
    for f in files:
        body = strip_md(f.read_text(encoding="utf-8", errors="replace"))
        if len(body) < 40:
            continue
        title = f.stem
        # drop leading sort index like 017-
        title = re.sub(r"^\d+-", "", title)
        parts.append(f"\n\n----- {title} -----\n\n{body}")
        n += 1
    return "".join(parts) + "\n", n


def meta_yaml(meta: dict) -> str:
    lines = []
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for sk, sv in v.items():
                lines.append(f"  {sk}: {json.dumps(sv, ensure_ascii=False)}")
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def build(with_jinghuo: bool) -> None:
    ensure_clone()
    RAW.mkdir(parents=True, exist_ok=True)
    vol_dir = RAW / "volumes"
    vol_dir.mkdir(parents=True, exist_ok=True)

    official_parts: list[str] = ["毛泽东选集（官方第一至五卷）\n来源: NpTIme/MaoZeDongAnthology\n"]
    essay_counts: dict[str, int] = {}
    total_essays = 0
    for code, dirname, label in OFFICIAL_DIRS:
        text, n = collect_volume(dirname, label)
        essay_counts[label] = n
        total_essays += n
        path = vol_dir / f"卷{code}_{label.split('（')[0]}.txt"
        path.write_text(text, encoding="utf-8")
        official_parts.append(text)
        print(f"OK {label}: {n} essays → {path.name} ({path.stat().st_size} bytes)")

    full = "\n".join(official_parts)
    full = re.sub(r"\n{3,}", "\n\n", full).strip() + "\n"
    full_path = RAW / "毛泽东选集_1-5卷.txt"
    full_path.write_text(full, encoding="utf-8")
    print(f"OK full official: {full_path} ({full_path.stat().st_size} bytes, {len(full)} chars, {total_essays} essays)")

    # smoke: key essays present
    for needle in ["实践论", "矛盾论", "反对本本主义", "改造我们的学习", "为人民服务", "论持久战"]:
        if needle not in full:
            raise RuntimeError(f"missing expected essay marker: {needle}")

    jinghuo_note = None
    if with_jinghuo:
        jh_parts = ["毛泽东选集 静火非官方卷六–卷七（鉴别使用）\n"]
        jh_n = 0
        for code, dirname, label in UNOFFICIAL_DIRS:
            text, n = collect_volume(dirname, label)
            jh_n += n
            path = vol_dir / f"卷{code}_{label}.txt"
            path.write_text(text, encoding="utf-8")
            jh_parts.append(text)
            print(f"OK {label}: {n} essays → {path.name}")
        jh = "\n".join(jh_parts)
        jh_path = RAW / "毛泽东选集_6-7卷_静火非官方.txt"
        jh_path.write_text(jh, encoding="utf-8")
        jinghuo_note = {
            "file": jh_path.name,
            "essays": jh_n,
            "warning": "unofficial Jinghuo compilation; not CCP official Selected Works",
        }
        print(f"OK jinghuo: {jh_path} ({jh_path.stat().st_size} bytes)")

    meta = {
        "book_id": "mao_selected_works",
        "title": "毛泽东选集",
        "title_en": "Selected Works of Mao Zedong",
        "box": "epistemology",
        "language": "zh",
        "coverage": "official_vols_1_to_5",
        "edition_note": "Official Selected Works vols 1–5 via NpTIme/MaoZeDongAnthology Markdown; personal research corpus",
        "source_url": REPO,
        "license": "source-noted; personal research corpus (not for commercial redistribution)",
        "ingest_status": "ready",
        "answer_language": "zh",
        "retrieval_language": "zh",
        "preferred_text": "毛泽东选集_1-5卷.txt",
        "source_adapter": "git_markdown_anthology",
        "essay_counts": essay_counts,
        "total_essays": total_essays,
        "char_count": len(full),
        "bytes": full_path.stat().st_size,
        "supersedes": "mao_selected_methods",
    }
    if jinghuo_note:
        meta["unofficial_jinghuo"] = jinghuo_note
    (RAW / "META.yaml").write_text(meta_yaml(meta), encoding="utf-8")
    print("wrote META.yaml")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--with-jinghuo",
        action="store_true",
        help="Also pack unofficial vols 6–7 (Jinghuo) as separate file",
    )
    args = ap.parse_args()
    build(with_jinghuo=args.with_jinghuo)


if __name__ == "__main__":
    main()
