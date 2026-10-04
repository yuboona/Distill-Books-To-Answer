# scripts

| 脚本 | 作用 |
|------|------|
| `bootstrap_corpus.py` | **书单 → 目录骨架 + META**（元 skill BUILD B0–B1） |
| `fetch_from_booklist.py` | **书单驱动统一抓取**（adapters） |
| `adapters/` | marxists / wikisource / gutenberg / github_raw / kanripo / … |
| `fetch_planned_three.py` | 盐铁论 / 传习录 / 毛选方法篇选（旧入口；优先用 booklist） |
| `fetch_mao_selected_works.py` | 毛泽东选集官方1–5（由 booklist adapter 调用） |
| `ingest.py` | **raw → chunks/*.jsonl** |
| `retrieve.py` | 优先扫 chunks；否则 raw 窗口 → Context Pack |
| `verify_quotes.py` | 引文必须是 Pack 原文子串 |
| `verify_curated_quotes.py` | 校验金句库每条锚定 chunk |
| `run_eval.py` | eval/cases.jsonl 回归（retrieve + verify） |
| `pack_skill.py` | 把 scripts/docs/templates 打进个人 skill 包（**不**含正文） |
| `run_coldstart.py` | 空库 L0 + 临时 2 书 BUILD 验收 |
| `clean_from_cache.py` | 从本地网页快照清洗入库 |
| `fetch_and_clean.py` | 在线抓取清洗（网络可用时） |
| `fetch_shiji_tongjian_full.py` / `fetch_tongjian_loop.sh` | 史记/通鉴全量（待收成 adapter） |

## 示例

```bash
python3 scripts/bootstrap_corpus.py --status
python3 scripts/ingest.py
python3 scripts/retrieve.py --query "被人爱戴好还是让人畏惧好" --out pack.json
python3 scripts/verify_quotes.py --pack pack.json --quote 'whether it be better to be loved than feared'
```

书单真源：`corpus/BOOKLIST.yaml`。
