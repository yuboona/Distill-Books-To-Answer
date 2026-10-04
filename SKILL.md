---
name: shi-shi-qiu-shi
description: >-
  Meta-skill: build a grounded classical/Maoist corpus from a booklist, then counsel
  life/career/relationship decisions only from retrieved original text (Zizhi Tongjian,
  Shiji, Mao Selected Works, Sunzi, Yangming, Dao De Jing, The Prince, Meditations, etc.).
  Use for 实事求是, 以史为镜, 知行合一, corpus bootstrap, or first-principles judgment;
  also when the user asks to build/ingest/retrieve a personal canon knowledge base.
---

# 实事求是 · Shi-Shi-Qiu-Shi（元 Skill）

用「事实—矛盾—实践」框架做判断；**论据只能来自已入库、已检索到的原文**。  
本 skill 有两种模式：**BUILD（建库）** 与 **COUNSEL（答问）**。无 ready 语料时禁止假引典。

工程真源：本 skill 包内 `scripts/` + `docs/`（语料正文**不在包内**）。  
若工作区有 `05-shi-shi-qiu-shi/`，那是开发沙盒 + 默认实例库。

## 何时启用

- 人生/职业/关系/资源两难、焦虑、站位、进退
- 需要第一性原理或古典/毛选方法智慧
- 用户要**按书单建知识库**、ingest、检索、校验引文
- 点名本 skill，或提到实事求是、以史为镜、知行合一、实践论等

## 启动时先判定模式

```text
探测 corpus：
  SSQS_CORPUS_ROOT → 工作区 05-shi-shi-qiu-shi/corpus → ./corpus → skill 内空骨架
脚本：
  工作区 05-shi-shi-qiu-shi/scripts（开发时）否则用本 skill 的 scripts/
  ├─ 用户明确要求建库 / 无 ready 书 / 无 chunks → Mode BUILD
  └─ 有 chunks 且是人生/决策咨询 → Mode COUNSEL
```

```bash
SKILL="$HOME/.cursor/skills/shi-shi-qiu-shi"
if [ -d 05-shi-shi-qiu-shi/scripts ]; then SCRIPTS=05-shi-shi-qiu-shi/scripts
elif [ -d "$SKILL/scripts" ]; then SCRIPTS="$SKILL/scripts"
fi
if [ -n "$SSQS_CORPUS_ROOT" ]; then CORPUS="$SSQS_CORPUS_ROOT"
elif [ -d 05-shi-shi-qiu-shi/corpus ]; then CORPUS=05-shi-shi-qiu-shi/corpus
elif [ -d corpus ]; then CORPUS=corpus
else CORPUS="$SKILL/corpus"
fi
export SSQS_CORPUS_ROOT="$CORPUS"
python3 "$SCRIPTS/bootstrap_corpus.py" --status --corpus-root "$CORPUS"
# ready_with_text>=1 且 $CORPUS/chunks/*.jsonl 存在 → 可 COUNSEL 引典
# 否则 BUILD 或 L0，禁止假引典
```

---

## Mode BUILD · 建库

目标：按书单把本地 `corpus/` 建成可检索、可校验的知识库。语料正文**不随 skill 分发**。

1. 确认/复制书单：`cp templates/BOOKLIST.example.yaml "$CORPUS/BOOKLIST.yaml"`（可改）  
2. `python3 "$SCRIPTS/bootstrap_corpus.py" --corpus-root "$CORPUS"`  
3. `python3 "$SCRIPTS/fetch_from_booklist.py" --corpus-root "$CORPUS"`（可用 `--only` / `--force`；无网时改 `local_path`）  
4. `python3 "$SCRIPTS/ingest.py" --corpus-root "$CORPUS"`  
5. Smoke：`retrieve.py --corpus-root "$CORPUS"` + `verify_quotes.py`  
6. 仅 `ingest_status: ready` 的书进入 COUNSEL  

无网络/无版权清晰源时：停在 planned，向用户说明，**不要用模型记忆冒充原文**。

---

## Mode COUNSEL · 答问

### 咨询工作流（每次必走）

```
问题进展:
- [ ] 0. 探测语料（无库→BUILD 或 L0，不引典）
- [ ] 1. 定事实
- [ ] 2. 定矛盾（一个主矛盾）
- [ ] 3. 定约束
- [ ] 4. 调 Context Pack（检索±改写查询→校验）
- [ ] 5. 给方略（上中下策 + 不可做）
- [ ] 6. 落实践（7 日内最小动作）
- [ ] 7. 设复盘
```

### 0–3 · 事实 / 矛盾 / 约束

同前：可观察事实；只立一个主矛盾；标出权力、资源、时间、关系、名誉；假可执行建议直接否决。缺关键事实先问 1–2 个问题。

### 4 · 调 Context Pack（有库则强制）

工作区或 `$CORPUS` 有 chunks 时：

1. **Pass-1**（用户**简体原问**）：
   ```bash
   python3 "$SCRIPTS/retrieve.py" --corpus-root "$CORPUS" --query "<原问>" --out pack.json
   ```
2. 若路由到繁体底本（通鉴等）或英文底本（君主论/沉思录），或 `low_confidence`：  
   模型可改写 1–3 条**等价繁体/英文检索短句**（Phase A 权宜，只为补字形/译词假阴性，**不得**用先验教义抢路由或开新书箱）→ **Pass-2**：
   ```bash
   python3 "$SCRIPTS/retrieve.py" --corpus-root "$CORPUS" --query "<原问>" \
     --extra-queries "…" "…" --out pack.json
   ```
3. 起草时「原文依据」**只能**来自 `pack.json` 的 `chunks[].text`（底本原文：简/繁/英原样）  
4. 英/繁可附「意译非原文」；分析与方略用中文  
5. 校验：
   ```bash
   python3 "$SCRIPTS/verify_quotes.py" --pack pack.json --quote '…'
   ```
   FAIL → 改写引文或删引，不得强行输出假原文  
6. 仍无命中 → **L0**：只谈方法/提问，明确「库中未检索到可引段落」

无项目语料时：可用 [lenses.md](lenses.md) 做结构类比，但必须标明**非原文核对**；禁止伪造篇名与引号内「原文」。

透镜：只选 1–2 个；类比讲结构；不把毛选当口号；权术类（《君主论》）必须附合法性/伤害红线。

### 5–7 · 方略 / 实践 / 复盘

| 档 | 含义 |
|----|------|
| 上策 | 代价可接受、直击主矛盾 |
| 中策 | 折中、买时间或保选项 |
| 不可做 | 情绪解气毁局，或假可执行 |

一个 7 日内可验证最小动作；2–3 个复盘信号。

## 输出模板

```markdown
## 事实澄清
- …

## 主矛盾
一句话：…

## 原文依据
1. 《书名》locus：
   > …底本原文…
   （意译……——意译非原文）  ← 仅英/繁需要时

## 据文分析
- …

## 方略
- 上策：…
- 中策：…
- 不可做：…

## 七日内最小动作
1. …

## 复盘信号
- 继续：…
- 改策：…
```

无 Pack 时删除「原文依据」，改为「方法提示（未核对原文）」。

## 默认书箱（用法索引）

详见 [canon.md](canon.md)。常备：史记、通鉴、实践论/矛盾论/毛选、孙子、传习录、道德经、沉思录、君主论、盐铁论。  
只引真正服务当前问题的 1–3 处；禁止堆砌。

## 硬性禁止

- 无 ready 语料或检索失败仍写「书中曰」+ 引号原文  
- 把检索改写句、意译、模型记忆当成原文  
- 用改写把原问锁进模型爱用的范畴，却声称「库自己选的」  
- 繁简折叠后再拿去过 Verifier  
- 算命/风水/宿命；违法或伤害他人；鸡汤代替约束分析  
- 一次堆超过 3 本典籍的大而全综述  

## 与其他框架

职业/副业执行清单可指向用户项目文档；本 skill 做人与局的判断，不替代表格填写。

透镜与反模式：[lenses.md](lenses.md)；示例：[examples.md](examples.md)。  
工程规范：本 skill 的 `docs/`（尤其 05/06/12/13）。开发沙盒：`05-shi-shi-qiu-shi/`。
