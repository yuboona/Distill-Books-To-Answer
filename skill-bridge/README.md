# skill-bridge

Agent 对接本项目的操作卡。产品形态：**元 skill = BUILD + COUNSEL**。规范：`docs/13-meta-skill.md`。

个人 skill：`~/.cursor/skills/shi-shi-qiu-shi/SKILL.md`（已含双模式）。

## 0. 探测

```bash
cd 05-shi-shi-qiu-shi
python3 scripts/bootstrap_corpus.py --status --corpus-root corpus
ls corpus/chunks/*.jsonl | wc -l
```

- `ready_with_text >= 1` 且已有 chunks → 允许 COUNSEL 引典  
- 否则 → Mode BUILD，或 COUNSEL 的 L0（不引典）

## Mode BUILD

```bash
python3 scripts/bootstrap_corpus.py
# 按 BOOKLIST 统一抓取（已有正文默认跳过；--force 重抓）
https_proxy=http://127.0.0.1:7890 python3 scripts/fetch_from_booklist.py --status
https_proxy=http://127.0.0.1:7890 python3 scripts/fetch_from_booklist.py --only on_practice
python3 scripts/ingest.py
python3 scripts/retrieve.py --query "实践" --out pack.json
```

书单二次变化：只改 `corpus/BOOKLIST.yaml`。

## Mode COUNSEL

```bash
# Pass-1
python3 scripts/retrieve.py --query "用户简体原问" --out pack.json

# Pass-2（繁体/英文弱命中时）
python3 scripts/retrieve.py --query "用户简体原问" \
  --extra-queries "玄武門之變" "loved than feared" \
  --out pack.json

# 校验（引文必须是 pack 子串；不做繁简折叠）
python3 scripts/verify_quotes.py --pack pack.json --quote '……原文……'
```

作答规则：

1. 「原文依据」只贴 `chunks[].text`  
2. `rewritten_queries` 禁止进依据栏  
3. `retrieval_language: en` → 引英文，分析中文（可意译并标明）  
4. 繁体命中 → 依据贴繁体，分析用简体  
5. `low_confidence` 且 Pass-2 仍弱 → L0 拒引  

细则：`docs/05-generation-protocol.md`、`docs/06-verification.md`、`docs/11-bilingual-retrieval.md`、`docs/12-script-language-retrieval.md`。

## 待补

- （M2 已完成）skill 包含脚本/docs；正文仍仅在本地 corpus  
- 网络不可用时 BUILD 走 `local_path`（`run_coldstart.py` 已覆盖）  
