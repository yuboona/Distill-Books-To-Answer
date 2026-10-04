# eval

检索 + 引文校验回归。

| 文件 | 内容 |
|------|------|
| `cases.jsonl` | ≥20 题：命中 / 拒假引 / 繁简 Verifier / 中英 |
| 跑分 | `python3 scripts/run_eval.py` |

```bash
cd 05-shi-shi-qiu-shi
python3 scripts/run_eval.py
python3 scripts/run_eval.py --only e04-prince-loved,v02-verify-fail-fake
python3 scripts/run_coldstart.py
```

期望：全部 PASS（exit 0）。Phase C 扩到 ≥50 题。
