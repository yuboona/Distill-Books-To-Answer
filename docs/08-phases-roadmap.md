# 08 · 实施路线图（Phases）

## Phase M — 元 skill 合流（与 A 并行规划）

目标：他人拿到 skill **不含你的语料**，仍能按书单自建库再答问。见 [13-meta-skill.md](13-meta-skill.md)。

- [x] `BOOKLIST.yaml` + `bootstrap_corpus.py`
- [x] 将现有 fetch/clean 收成可插拔 adapter — **`scripts/fetch_from_booklist.py` + `adapters/`**
- [x] Skill `SKILL.md` 增加 Mode BUILD / Mode COUNSEL
- [x] corpus 正文默认不进 skill 分发包 — **`scripts/pack_skill.py` → `~/.cursor/skills/shi-shi-qiu-shi`（无 raw/chunks 正文）**
- [x] 空库冷启动验收（§8） — **`python3 scripts/run_coldstart.py`（空库 L0 + 临时 2 书 BUILD）**

## Phase 0 — 规划就位（当前）

- [x] 项目目录 `05-shi-shi-qiu-shi/`  
- [x] 架构与规范 Markdown  
- [x] corpus/scripts/eval/skill-bridge 占位  
- [ ] 尚无语料正文、尚无 retrieve/verify 脚本  

## Phase A — 可信最小版（优先）

目标：无向量也能 **L0–L3** 可用。

1. 选定底本与版权清晰的文本，先收：  
   - 实践论、矛盾论、孙子、道德经  
   - 盐铁论、君主论（中译注明）  
   - 史记/通鉴各若干高密度篇  
2. 编写 `META.yaml` + `MANIFEST.md`  
3. 切块脚本 `scripts/ingest.py` → `corpus/chunks/*.jsonl`  
4. `scripts/retrieve.py`：路由 + 繁简折叠 + 中英分检 + **Skill 模型改写查询（`--extra-queries`）** + 字数配额 → `pack.json`（规范：[12-script-language-retrieval.md](12-script-language-retrieval.md)）  
5. `scripts/verify_quotes.py`  
6. `eval/` 准备 ≥20 道题（含应拒答题） — **已有 `eval/cases.jsonl` + `scripts/run_eval.py`**  
7. 更新 `~/.cursor/skills/shi-shi-qiu-shi` 强制走本管道  
8. 人工金句库起步（30～80 条核验引文） — **已有 `quotes/curated.jsonl`（38 条）+ verify/boost**  

**验收：** 随机 10 答，引文 100% 能在 chunks 中搜到；3 道库外题全部拒引。

## Phase B — 标准 RAG

1. 向量索引与稀疏融合（**对用户原问**检索，减少模型改写）  
2. **库证扩词** + rerank：`--extra-queries` 须在 chunks/curated/BOOKLIST 出现，否则丢弃；OpenCC/zhconv；专名别名从库核验  
3. 扩大通鉴/史记/毛选方法篇覆盖  
4. 简单前端或 CLI 一键 `ask.py`（检索→生成提示词包→校验）  
5. Pack 标明命中来自原问还是改写；改写独有块降权

**验收：** 延迟与命中率可接受；评测集「乱引率」低于约定阈值。

## Phase C — 强约束与版本

1. 多译本/异文说明（L4）  
2. 金句库扩大 + 优先召回  
3. 评测集 ≥50 题，CI 可跑 verify  
4. 覆盖率仪表盘（每书字数、就绪状态）

## 建议的近期顺序（执行时勾选）

- [ ] 冻结 Phase A 书单与版权来源  
- [ ] 导入第一批全文（实践论/矛盾论/孙子）  
- [x] ingest + retrieve + verify 跑通 Hello World  
- [ ] 盐铁论、君主论入库与路由规则实测  
- [ ] 回写 skill-bridge 与个人 SKILL.md  
