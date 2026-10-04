# 04 · 检索设计（Retrieval）

## 为何必须混合检索

人生问题是现代语义；典籍是史事与范畴语言。纯向量易「语义像但不相关」。故：

**Router 限书箱 → 稀疏检索抓专名/范畴 → 向量补意图 → Rerank 成 Pack。**

## Router

输入：用户问题。输出：有序 `box[]` + 可选 `book_id[]` + `rewritten_queries[]`。

规则表见 [09-canon-router.md](09-canon-router.md)。

查询改写（Phase A **权宜**；检索专用，见 [12 §3.6](12-script-language-retrieval.md)）：

- 生成 2–3 条「更像书中会说的话」的检索短句，**同时保留用户原句**  
- 目标含繁体底本：额外产出等价**繁体**短句/关键词（例：玄武门 → 玄武門、建成、世民）  
- 目标含英文底本：额外产出等价**英文**短句/关键词（见 [11](11-bilingual-retrieval.md)、[12](12-script-language-retrieval.md)）  
- 改写句只进 `rewritten_queries` / `--extra-queries`，**禁止**当作原文依据  
- **倾向性**：模型看不见全书，改写会把先验范畴塞进检索；合法引文仍可能选题被带偏。后续应用**库内可核验**的扩词替代加重改写  

推荐两趟：

1. Pass-1：用户原问 + 确定性 fold + 意图表（不开新书箱）  
2. 若 `low_confidence` 或路由到繁/英书：Skill 改写 → Pass-2 带 `--extra-queries`（只补字形/译词假阴性）
## Phase A：无向量也可用

1. 按 Router 打开的 `book_id` 限制文件范围  
2. `rg` / 简易 BM25 对 `chunks/*.jsonl` 的 `text` 与 `locus` 检索  
3. 金句库 `quotes/curated.jsonl` 优先命中则提升排序  
4. 取 Top-K（建议 K=6～12），总字数硬顶 **3000～6000**  
5. 每书最多 N 块（建议 N=4），防止一书垄断  

## Phase B：标准 RAG

- 嵌入模型本地或 API；库用 Chroma / LanceDB / SQLite-vec  
- 稀疏 + 稠密分数融合（如 RRF）  
- Cross-encoder rerank（可选）  

## Context Pack 合同

字段最小集：

| 字段 | 说明 |
|------|------|
| `query` | 原问题 |
| `rewritten_queries` | 模型/规则改写的繁体或英文检索句（可空） |
| `boxes` | 路由书箱 |
| `chunks[]` | id/book/locus/text/score |
| `total_chars` | 合计 |
| `low_confidence` | 最高分低于阈值或结果过少时为 true |

### low_confidence 建议阈值（可调）

- 命中 chunks < 2  
- 或最高 score 低于经验阈值（Phase A 可用命中词数代替）  

此时生成器 **L0 拒引**。

## 检索接口（规划）

```bash
# Phase A CLI
python scripts/retrieve.py --query "用户简体原问" --out pack.json
# 弱命中后二次检索（Skill 先改写）
python scripts/retrieve.py --query "用户简体原问" \
  --extra-queries "玄武門之變" "whether it be better to be loved than feared" \
  --out pack.json
```

返回唯一真相包；生成侧只读该文件。

## 脚本与语言折叠（强制）

检索匹配必须遵守 [12-script-language-retrieval.md](12-script-language-retrieval.md)：

- **繁简：** 匹配键上做繁→简折叠；不够时允许 Skill 产出繁体等价查询再检；入库与引用保持底本。  
- **中英：** 中文书用中文词；英文书用意图表或 Skill 改写的英文词；引用英文原句，分析用中文。  
- **校验：** 不做折叠/回译；引文必须是原文子串；改写查询句不得冒充原文。
