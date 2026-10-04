# 06 · 引用校验（Verification）

无 Verifier 的 RAG 只是「检索增强的更会编」。校验是保真闭环。

## 校验算法（Phase A）

对助手输出中每一条原文依据：

1. 抽出引号内文本 `q`（归一化：去空白、统一引号/句读可选）  
2. 在本次 Context Pack 的所有 `chunk.text` 中查找：`q` 是否为**连续子串**  
3. 检查声称的 `book` + `locus` 是否与命中 chunk 的元数据一致（允许 locus 别名表）  
4. 任一条失败 → 该条 FAIL  

聚合：

- 全部 PASS → 可展示  
- 部分 FAIL → 剔除失败条后重评；若剩余 < 1 且声称「有典据」→ 整答降级 L0  
- 故意要求强建议（上策）时可配置：**至少 2 条独立 locus PASS**

## CLI（规划）

```bash
python scripts/verify_quotes.py --pack pack.json --answer answer.md
# exit 0: OK
# exit 1: 打印失败引文与原因
```

## 归一化规则（建议）

- Unicode 全半角括号、异体「说/曰」不强制统一原文，避免误伤  
- 仅压缩空白与换行  
- 禁止「模糊匹配到 80% 就算」——保真优先于召回  
- **不做繁简折叠、不做英汉互译后再比对。** 简体「司马光」不能拿来当繁体「司馬光」原文过关。匹配阶段的折叠不得进入 Verifier。

## 与人工金句库

若引文来自 `quotes/curated.jsonl` 且 `chunk_id` 有效，仍须能在对应 chunk 中找到子串（金句不得脱离 chunk 悬空）。

## 评测挂钩

`eval/` 中应包含：

- 正确引文样例 → 必须 PASS  
- 篡改一字的假引文 → 必须 FAIL  
- 张冠李戴 book/locus → 必须 FAIL  
