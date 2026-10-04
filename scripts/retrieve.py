#!/usr/bin/env python3
"""Keyword retrieve over corpus/raw (Phase A).

Match keys: lowercase + traditional-to-simplified fold.
Citations: original corpus text only (see docs/12-script-language-retrieval.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import chunks_dir, corpus_root, quotes_path, raw_dir  # noqa: E402
from zh_fold import both_script_forms, fold_for_match  # noqa: E402

RAW = raw_dir()
CHUNKS_DIR = chunks_dir()
QUOTES_PATH = quotes_path()


def bind(corpus: Path | str | None = None) -> Path:
    global RAW, CHUNKS_DIR, QUOTES_PATH
    c = corpus_root(corpus)
    RAW = raw_dir(c)
    CHUNKS_DIR = chunks_dir(c)
    QUOTES_PATH = quotes_path(c)
    return c

BOX_BOOKS = {
    "epistemology": ["on_practice", "on_contradiction", "mao_selected_works"],
    "strategy": ["sunzi", "the_prince"],
    "cultivation": ["dao_de_jing", "meditations", "chuanxilu"],
    "history": ["shiji", "zizhi_tongjian"],
    "policy_debate": ["yan_tie_lun"],
}

PREFERRED_TEXT = {
    "shiji": "史记.简体.txt",
    "zizhi_tongjian": "资治通鉴_全文.txt",
    "the_prince": "the_prince_marriott.txt",
    "meditations": "meditations_pg2680.txt",
    "on_practice": "实践论.txt",
    "on_contradiction": "矛盾论.txt",
    "sunzi": "孙子兵法.txt",
    "dao_de_jing": "道德经.txt",
    "yan_tie_lun": "盐铁论.txt",
    "chuanxilu": "传习录.txt",
    "mao_selected_works": "毛泽东选集_1-5卷.txt",
}

# Chinese intent -> English terms for EN-source books
ZH_TO_EN = [
    (re.compile(r"爱|怕|恐惧|畏惧|仁慈|残暴|愛|懼|殘"), ["loved", "feared", "cruelty", "clemency"]),
    (re.compile(r"新主|新岗位|站稳|巩固|鞏固"), ["new principalities", "own arms", "fortune"]),
    (re.compile(r"雇佣|外援|同盟|背刺|僱傭"), ["mercenaries", "auxiliaries", "faith"]),
    (re.compile(r"可控|情绪|职责|苦难|情緒|職責|苦難"), ["opinion", "duty", "obstacle", "mind"]),
]


def guess_boxes(query: str) -> list[str]:
    q = fold_for_match(query)
    boxes = []
    if re.search(r"实践|认识|调查|落地|空谈|检验|本本|整风|毛选|毛泽东|持久战|统一战线", q):
        boxes.append("epistemology")
    if re.search(r"矛盾|重点|主次|优先级", q):
        boxes.append("epistemology")
    if re.search(r"盐铁|专营|民本|桑弘|贤良|文学议", q):
        boxes.append("policy_debate")
    if re.search(r"战|谈判|刚|攻|守|势力|权力|怕|爱戴|同盟", q):
        boxes.append("strategy")
    if re.search(r"知行|焦虑|情绪|知止|无为|内心|良知|阳明|上善|若水|道德经", q):
        boxes.append("cultivation")
    if re.search(r"进退|权柄|站队|功高|君臣|史记|通鉴|通鑑|项羽|高祖|留侯|司马|玄武|建成|世民|太宗|赤壁|淝水", q):
        boxes.append("history")
    if not boxes:
        boxes = ["epistemology", "strategy"]
    seen: set[str] = set()
    out: list[str] = []
    for b in boxes:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out[:2]


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        t = t.strip()
        if len(t) < 2:
            continue
        key = fold_for_match(t)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def expand_terms(query: str, extra_queries: list[str] | None = None) -> list[str]:
    """Expand match terms from user query + optional model-rewritten queries.

    extra_queries: Skill/model 产出的繁体或英文等价检索句；只用于匹配，不是原文。
    """
    sources = [query] + list(extra_queries or [])
    terms: list[str] = []
    for src in sources:
        terms.extend(re.findall(r"[A-Za-z']{3,}", src))
        # Multi-word English phrases as single match keys
        for phrase in re.findall(r"[A-Za-z][A-Za-z' ]{4,}[A-Za-z]", src):
            terms.append(phrase.strip())
        q_fold = fold_for_match(src)
        for cre, en_terms in ZH_TO_EN:
            if cre.search(src) or cre.search(q_fold):
                terms.extend(en_terms)
        lexicon = [
            "实践", "认识", "真理", "矛盾", "调查", "感性", "理性",
            "知行", "兵者", "谋攻", "虚实", "无为", "上善",
            "loved", "feared", "arms", "fortune",
            "司马光", "司馬光", "项羽", "項羽",
        ]
        for w in lexicon:
            if fold_for_match(w) in q_fold or w.lower() in src.lower():
                terms.extend(both_script_forms(w) if re.search(r"[\u4e00-\u9fff]", w) else [w])
        zh = "".join(re.findall(r"[\u4e00-\u9fff]", src))
        for n in (2, 3):
            for i in range(0, max(0, len(zh) - n + 1)):
                terms.extend(both_script_forms(zh[i : i + n]))
    return _dedupe_terms(terms)


def iter_windows(text: str, size: int = 400, stride: int = 300):
    i = 0
    n = len(text)
    idx = 0
    while i < n:
        yield idx, text[i : i + size]
        idx += 1
        if i + size >= n:
            break
        i += stride


def score_window(window: str, terms: list[str], lang: str) -> float:
    if lang == "en":
        w = window.lower()
        score = 0.0
        for t in terms:
            if re.fullmatch(r"[a-zA-Z' ]+", t) and t.lower() in w:
                score += 1.0 + min(len(t), 12) / 12.0
        return score
    w = fold_for_match(window)
    score = 0.0
    for t in terms:
        if re.fullmatch(r"[a-zA-Z' ]+", t):
            continue
        tf = fold_for_match(t)
        if tf in w:
            score += 1.0 + min(len(tf), 12) / 12.0
    return score


def load_chunks(book_id: str) -> list[dict] | None:
    path = CHUNKS_DIR / f"{book_id}.jsonl"
    if not path.exists():
        return None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows or None


def load_curated() -> list[dict]:
    if not QUOTES_PATH.exists():
        return []
    rows = []
    for line in QUOTES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def curated_boosts(query: str, extras: list[str], book_ids: list[str]) -> dict[str, float]:
    """Return chunk_id -> bonus score when curated quote matches query."""
    q_fold = fold_for_match(" ".join([query] + extras))
    q_raw = " ".join([query] + extras)
    bonuses: dict[str, float] = {}
    for row in load_curated():
        if row.get("book_id") not in book_ids:
            continue
        quote = row.get("quote") or ""
        tags = row.get("tags") or []
        hit = False
        qf = fold_for_match(quote)
        if len(qf) >= 2 and qf in q_fold:
            hit = True
        if not hit:
            for tag in tags:
                tf = fold_for_match(str(tag))
                if len(tf) >= 2 and tf in q_fold:
                    hit = True
                    break
        if not hit and quote.lower() in q_raw.lower():
            hit = True
        if hit:
            cid = row.get("chunk_id")
            if cid:
                bonuses[cid] = max(bonuses.get(cid, 0.0), 8.0)
    return bonuses


def load_chunk_by_id(book_id: str, chunk_id: str) -> dict | None:
    rows = load_chunks(book_id)
    if not rows:
        return None
    for row in rows:
        if row.get("id") == chunk_id:
            return row
    return None


def load_book_text(book_id: str) -> tuple[str, str] | None:
    d = RAW / book_id
    if not d.exists():
        return None
    preferred = PREFERRED_TEXT.get(book_id)
    path = d / preferred if preferred else None
    if path is None or not path.exists():
        path = next(d.glob("*.txt"), None)
    if not path:
        return None
    meta_path = d / "META.yaml"
    retrieval_lang = "zh"
    if meta_path.exists():
        m = meta_path.read_text(encoding="utf-8")
        if 'retrieval_language: "en"' in m or "retrieval_language: en" in m:
            retrieval_lang = "en"
    return path.read_text(encoding="utf-8"), retrieval_lang


def score_chunk_rows(book_id: str, rows: list[dict], terms: list[str]) -> list[dict]:
    hits = []
    for row in rows:
        lang = row.get("retrieval_language") or "zh"
        sc = score_window(row["text"], terms, lang)
        if sc <= 0:
            continue
        hits.append(
            {
                "id": row["id"],
                "book_id": book_id,
                "locus": row.get("locus") or book_id,
                "text": row["text"],
                "score": round(sc, 3),
                "retrieval_language": lang,
                "match_mode": "en" if lang == "en" else "zh_fold",
                "source": "chunks",
            }
        )
    return hits


def retrieve(
    query: str,
    top_k: int = 8,
    extra_queries: list[str] | None = None,
) -> dict:
    extras = [q.strip() for q in (extra_queries or []) if q and q.strip()]
    boxes = guess_boxes(query)
    for eq in extras:
        for b in guess_boxes(eq):
            if b not in boxes:
                boxes.append(b)
    boxes = boxes[:3]
    terms = expand_terms(query, extras)
    book_ids: list[str] = []
    for b in boxes:
        for bid in BOX_BOOKS.get(b, []):
            if bid not in book_ids:
                book_ids.append(bid)

    hits: list[dict] = []
    used_chunks = False
    bonuses = curated_boosts(query, extras, book_ids)
    for book_id in book_ids:
        rows = load_chunks(book_id)
        if rows:
            used_chunks = True
            hits.extend(score_chunk_rows(book_id, rows, terms))
            continue
        # Fallback: sliding window over raw text
        loaded = load_book_text(book_id)
        if not loaded:
            continue
        text, retrieval_lang = loaded
        match_mode = "en" if retrieval_lang == "en" else "zh_fold"
        for wid, window in iter_windows(text):
            sc = score_window(window, terms, retrieval_lang)
            if sc <= 0:
                continue
            hits.append(
                {
                    "id": f"{book_id}-{wid:04d}",
                    "book_id": book_id,
                    "locus": f"{book_id}~win{wid}",
                    "text": window.strip(),
                    "score": round(sc, 3),
                    "retrieval_language": retrieval_lang,
                    "match_mode": match_mode,
                    "source": "raw_window",
                }
            )

    # Apply curated boosts; inject missing curated chunks if book in scope
    by_id = {h["id"]: h for h in hits}
    for cid, bonus in bonuses.items():
        if cid in by_id:
            by_id[cid]["score"] = round(by_id[cid]["score"] + bonus, 3)
            by_id[cid]["curated_boost"] = bonus
            by_id[cid]["source"] = "chunks+curated"
        else:
            book_id = "-".join(cid.split("-")[:-1])
            if book_id not in book_ids:
                continue
            row = load_chunk_by_id(book_id, cid)
            if not row:
                continue
            lang = row.get("retrieval_language") or "zh"
            hits.append(
                {
                    "id": cid,
                    "book_id": book_id,
                    "locus": row.get("locus") or book_id,
                    "text": row["text"],
                    "score": round(bonus, 3),
                    "retrieval_language": lang,
                    "match_mode": "en" if lang == "en" else "zh_fold",
                    "source": "curated",
                    "curated_boost": bonus,
                }
            )
            used_chunks = True

    hits.sort(key=lambda x: x["score"], reverse=True)
    picked = []
    per: dict[str, int] = {}
    for h in hits:
        c = per.get(h["book_id"], 0)
        if c >= 4:
            continue
        picked.append(h)
        per[h["book_id"]] = c + 1
        if len(picked) >= top_k:
            break

    return {
        "query": query,
        "rewritten_queries": extras,
        "expanded_terms": terms,
        "boxes": boxes,
        "chunks": picked,
        "total_chars": sum(len(c["text"]) for c in picked),
        "low_confidence": len(picked) < 2,
        "answer_language": "zh",
        "index": "chunks" if used_chunks else "raw_window",
        "note": (
            "Match: zh_fold + optional model-rewritten queries (--extra-queries). "
            "Prefer corpus/chunks/*.jsonl; curated.jsonl boosts matching chunk_ids. "
            "chunk.text is original script only; rewritten_queries are NOT citations. "
            "See docs/12-script-language-retrieval.md"
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument(
        "--extra-queries",
        nargs="*",
        default=[],
        help="Model-rewritten Trad/EN retrieval strings (Skill-driven; not citations)",
    )
    ap.add_argument("--out", default="")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--corpus-root", type=Path, default=None)
    args = ap.parse_args()
    bind(args.corpus_root)
    pack = retrieve(args.query, top_k=args.top_k, extra_queries=args.extra_queries)
    s = json.dumps(pack, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(s, encoding="utf-8")
        print(f"wrote {args.out} chunks={len(pack['chunks'])} low={pack['low_confidence']}")
    else:
        print(s)


if __name__ == "__main__":
    main()
