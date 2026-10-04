# 实事求是 · 原文接地咨询系统

本目录系统性搭建 **基于可信原文** 的人生/决策咨询能力，作为个人 skill `~/.cursor/skills/shi-shi-qiu-shi` 的项目侧真相源与工程实现。

**产品定位：** 元 skill（建库 + 据库答问）。语料正文是本地产物；可复用的是协议与脚本。见 [docs/13-meta-skill.md](docs/13-meta-skill.md)。

## 核心承诺

> 模型只能在「已检索到的原文片段」上分析；检索失败则拒引典籍，不许脑补成文。

Skill 管流程与方略模板；语料 + 检索 + 校验管「有没有书、是不是这本书里的话」。

## 目录结构

```text
05-shi-shi-qiu-shi/
├── README.md                 ← 本文件
├── docs/                     ← 方案与规范（先读这里）
├── corpus/
│   ├── raw/                  ← 原始文本（按书分目录）
│   ├── chunks/               ← 切块 + 元数据（检索单元）
│   └── quotes/               ← 人工核验金句快轨
├── scripts/                  ← retrieve / verify / ingest（Phase A 起实现）
├── eval/                     ← 评测题与回归
└── skill-bridge/             ← 与 ~/.cursor/skills/shi-shi-qiu-shi 的对接说明
```

## 文档导航

| 文档 | 内容 |
|------|------|
| [docs/00-overview.md](docs/00-overview.md) | 目标、原则、与现有 skill 关系 |
| [docs/01-fidelity-layers.md](docs/01-fidelity-layers.md) | 保真层级 L0–L4 |
| [docs/02-architecture.md](docs/02-architecture.md) | 总架构与数据流 |
| [docs/03-corpus.md](docs/03-corpus.md) | 语料规范、书箱、切块、版权 |
| [docs/04-retrieval.md](docs/04-retrieval.md) | 路由、混合检索、Context Pack |
| [docs/05-generation-protocol.md](docs/05-generation-protocol.md) | 先引后论、输出协议 |
| [docs/06-verification.md](docs/06-verification.md) | 引用校验与降级 |
| [docs/07-skill-integration.md](docs/07-skill-integration.md) | Cursor skill 对接 |
| [docs/08-phases-roadmap.md](docs/08-phases-roadmap.md) | Phase A/B/C 路线图 |
| [docs/09-canon-router.md](docs/09-canon-router.md) | 经籍箱与问题路由（含君主论、盐铁论） |
| [docs/10-book-sources.md](docs/10-book-sources.md) | **书单、文本源与质量裁定** |
| [docs/11-bilingual-retrieval.md](docs/11-bilingual-retrieval.md) | 英文本检索 + 中文作答（君主论/沉思录） |
| [docs/12-script-language-retrieval.md](docs/12-script-language-retrieval.md) | **繁简折叠 / 中英分检：匹配≠引用** |
| [docs/13-meta-skill.md](docs/13-meta-skill.md) | **元 skill：建库+答问合二为一；书单驱动** |
| [docs/14-answer-scheme.md](docs/14-answer-scheme.md) | **解答方案：语料 / 取证 / 判断 / 审计** |

## 当前阶段

**Phase A 可用 + Phase M2 已打包：** 11 书实例库；skill 包含脚本/文档、不含正文。  
```bash
python3 scripts/ingest.py
python3 scripts/retrieve.py --query "..." --out pack.json
python3 scripts/verify_quotes.py --pack pack.json --quote '...'
python3 scripts/run_coldstart.py
python3 scripts/pack_skill.py   # → ~/.cursor/skills/shi-shi-qiu-shi
```

## 快速原则（墙上贴纸）

1. 无检索，不引典  
2. 引文必须是 chunk 连续子串（**不**做繁简/翻译后再比）  
3. 「原文所述」与「延伸推论」分栏  
4. 一次主源 + 至多一辅源  
5. 《君主论》类权术分析必须附合法性/伤害红线  
6. 检索可繁简折叠、中英扩词；**引用永远用底本原文**
