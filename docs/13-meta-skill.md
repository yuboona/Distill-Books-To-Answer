# 13 · 元 Skill 架构：建库与答问合二为一

## 1. 对当前状态的裁定

| 问题 | 现状 | 目标 |
|------|------|------|
| corpus 构建流程可复用吗？ | **部分可复用、尚未产品化**。有 `META.yaml` 约定、清洗脚本、抓取脚本，但多绑死在「我们的书单 + 一次性 URL/代理」上 | **书单驱动的标准流水线**：他人换书单即可重建 |
| 已是 skill 的一部分吗？ | **否**。个人 skill 只管七步答问；语料在 `05-shi-shi-qiu-shi/corpus`；二者靠 bridge「共存配合」 | **一个 skill 两模式**：`build`（建库）+ `counsel`（答问） |
| 别人拿到 skill 能用吗？ | **不能开箱即用**。拿不到你的语料，也没有自动建库指引 | 拿到的是**元 skill**：按自己的书单跑通建库，再进入 grounded 答问 |
| 项目与 skill 该合二为一吗？ | 物理上已分叉（`~/.cursor/skills/...` vs 仓库子目录） | **逻辑合一、制品分离**：协议与脚本进 skill；**正文语料永远是本地产物，默认不随 skill 分发** |

一句话：

> 今日 = 咨询 skill + 工程沙盒（含你的私有/大体量语料）  
> 明日 = **元 skill**：教 Agent「如何从书单建成可校验知识库」，再建好后「如何只据库答问」

---

## 2. 产品形态（目标）

```text
用户给出 BOOKLIST.yaml（或沿用默认书单）
        │
        ▼
┌───────────────────────┐
│  Mode BUILD（建库）     │  ← 元 skill 核心可复用部分
│  源裁定 → 抓取/导入     │
│  → 清洗 → META/MANIFEST │
│  → ingest → smoke 检索  │
└───────────┬───────────┘
            │ 产出本地 corpus/（不进 skill 包）
            ▼
┌───────────────────────┐
│  Mode COUNSEL（答问）   │  ← 现有七步 + retrieve/verify
│  Router → 检索(+改写)   │
│  → Pack → 先引后论 → 校验│
└───────────────────────┘
```

### 2.1 Skill 包里有什么（可分发）

```text
shi-shi-qiu-shi/          # 或将来改名 grounded-canon / meta 名
├── SKILL.md              # 双模式入口 + 禁令
├── canon.md              # 默认透镜与用法（可覆盖）
├── lenses.md / examples.md
├── templates/
│   ├── BOOKLIST.example.yaml
│   └── META.example.yaml
├── docs/                 # 或精简引用：保真层、检索、繁简中英、生成协议
├── scripts/
│   ├── bootstrap_corpus.py   # 按书单建目录骨架
│   ├── fetch_*.py / clean_*.py  # 通用抓取清洗（可插拔 adapter）
│   ├── ingest.py
│   ├── retrieve.py
│   ├── verify_quotes.py
│   └── zh_fold.py
└── eval/smoke/           # 最小验收题模板（无正文）
```

**不进 skill 包：** `corpus/raw/**/*.txt`、通鉴全文、任何用户下载正文。  
Skill 只带「空 corpus 骨架说明」或 `.gitkeep`。

### 2.2 用户工作区有什么（私有）

```text
<任意项目或专用目录>/
└── corpus/                 # BUILD 产出；可 gitignore
    ├── BOOKLIST.yaml       # 用户书单（可从默认复制后改）
    ├── raw/<book_id>/...
    ├── chunks/
    └── quotes/
```

路径约定：skill 启动时探测 `./corpus` 或环境变量 `SSQS_CORPUS_ROOT`；没有则进入 **BUILD**，不假装能引典。

---

## 3. 书单驱动（二次变化的接口）

`BOOKLIST.yaml` 是他人定制的唯一主入口：

```yaml
corpus_root: ./corpus
defaults:
  answer_language: zh
  match: { script_fold: true, allow_query_rewrite: true }
books:
  - book_id: on_practice
    title: 实践论
    box: epistemology
    retrieval_language: zh
    source:
      type: url_html
      url: https://...
      adapter: marxists_html   # 可插拔清洗器
    license: public_domain_or_clear
    ingest_status: planned
  - book_id: the_prince
    box: strategy
    retrieval_language: en
    source: { type: gutenberg, id: 1232, adapter: gutenberg_txt }
  - book_id: my_notes
    box: custom
    retrieval_language: zh
    source: { type: local_path, path: ~/Docs/my.txt, adapter: plain_txt }
```

规则：

- **默认书单** = 我们冻结的 Phase A 推荐（可一键 bootstrap）  
- **换书** = 改 YAML，不改 skill 源码（新源类型才加 adapter）  
- `ingest_status != ready` 的书不进检索  

现有 `docs/10-book-sources.md` 降级为「默认书单的源裁定笔记」，不是唯一路径。

---

## 4. BUILD 流水线（可复用步骤）

必须变成 skill 可执行 checklist（Agent 逐步跑，不靠口头回忆）：

| 步 | 动作 | 产出 |
|----|------|------|
| B0 | 确认/生成 `BOOKLIST.yaml` | 用户书单 |
| B1 | `bootstrap_corpus` 建 `raw/<id>/META.yaml` | 骨架 |
| B2 | 按 `source.type` 调 adapter：抓取或拷贝 | `.download_tmp` / raw 候选 |
| B3 | 清洗（去导航、导言、页码噪声） | `raw/<id>/*.txt` |
| B4 | 填 `license` / `edition_note`；抽检关键句 | META 更新 |
| B5 | `ingest` → chunks JSONL | `chunks/` |
| B6 | smoke：`retrieve` + 预定验收句；繁简/中英规则生效 | 报告 |
| B7 | 标记 `ready`；写 MANIFEST | 可进入 COUNSEL |

失败策略：单书失败不阻断全书；该书写 `failed` + 原因，答问时 Router 跳过。

**当前缺口（更新）：**

- [x] `BOOKLIST` + `bootstrap`  
- [x] `ingest.py` / `verify_quotes.py`  
- [x] `fetch_from_booklist.py` + adapters（书单驱动）  
- [x] Skill 双模式入口  
- [x] 脚本/docs 物理并入 skill 包（Phase M2）  
- [x] 空库冷启动端到端验收  

---

## 5. COUNSEL 流水线（建库之后）

与现 [07](07-skill-integration.md)、[12](12-script-language-retrieval.md) 一致；前置条件改为：

- 若无 `corpus` 或 MANIFEST 无 `ready` 书 → **只允许 BUILD 或 L0 方法论**，禁止假引典  
- 有库 → Pass-1/Pass-2 检索 + 校验 + 七步方略  

---

## 6. 物理合并策略（推荐路径）

不必强行把 14MB 通鉴塞进 `~/.cursor/skills`。推荐：

### Phase M1（近）

1. 在仓库保留 `05-shi-shi-qiu-shi/` 作**开发沙盒 + 你的默认实例**  
2. 新增 `docs/13`（本文件）为产品真源  
3. 抽象：`BOOKLIST.yaml` + `bootstrap_corpus.py` + adapter 接口  
4. 个人 skill 增加 **Mode BUILD** 段落，指向本目录脚本（仍可 bridge）

### Phase M2（合）

1. 将 `docs/` 精要 + `scripts/`（无 raw 正文）打包进 skill：`python3 scripts/pack_skill.py`  
2. `corpus/` 默认 gitignore 正文；提供 `templates/BOOKLIST.example.yaml`  
3. `05-shi-shi-qiu-shi` 仍作开发沙盒 + 默认实例

### Phase M3（产品）

1. 对外名可定为「grounded canon meta-skill」  
2. 用户：粘贴书单 → Agent 建库 → 自动切换答问  
3. 可选：多知识库 profile（职业/家庭/研究）共用同一套协议  

---

## 7. 与「直接可用 skill」的边界

| | 直接可用咨询 skill（旧） | 元 skill（目标） |
|--|------------------------|------------------|
| 分发内容 | 流程 + 书名印象 | 流程 + **建库协议** + 检索/校验脚本 |
| 首次使用 | 立刻答，易假引文 | 先 BUILD（或声明无库） |
| 个性化 | 难（书写死在 prompt） | **书单二次变化** |
| 质量承诺 | 文风 | **可核对原文** |

我们接受：元 skill **不是开箱即答神谕**，而是开箱即**搭建可信决策模块**的脚手架。

---

## 8. 验收（元 skill 级）

跑：`python3 scripts/run_coldstart.py`

1. 空 corpus → retrieve 0 命中（COUNSEL 只能 L0，不得误引通鉴）  
2. 临时目录 + 书单重建至少 2 本（网络 fetch，或 `local_path`）→ ingest + 检索命中 + verify  
3. `python3 scripts/pack_skill.py` 后 skill 目录无 `*.txt` 正文  
4. COUNSEL 抽查引文 100% 为 chunk 子串  

---

## 9. 立即决策（已采纳）

1. **产品定位改为元 skill**（建库 + 答问），不再满足于「咨询 skill ∥ 工程目录」长期双轨。  
2. **语料正文永不作为 skill 必达附件**；默认可复用的是协议与脚本。  
3. **书单 YAML 为定制主接口**；当前抓取脚本演进为 adapter，而不是永久特判。  
4. 近端在本仓库落地 BOOKLIST + bootstrap；再回写 `~/.cursor/skills/shi-shi-qiu-shi` 的双模式入口。
