# 03 · 语料规范（Corpus）

## 目录约定

```text
corpus/
├── raw/           # 原始文本，一书一目录
│   └── <book_id>/
│       ├── META.yaml
│       └── *.txt | *.md
├── chunks/        # 检索单元 JSONL
│   └── <book_id>.jsonl
└── quotes/        # 人工核验金句
    └── curated.jsonl
```

## META.yaml 字段（每书必填）

```yaml
book_id: shiji
title: 史记
title_en: Records of the Grand Historian
box: history          # 见 09-canon-router
language: classical_zh
edition_note: "待填：底本/整理者/来源 URL"
license: "待填：公版或使用权说明"
ingest_status: planned  # planned | partial | ready
```

## 书箱与计划收录

| book_id | 书名 | box | Phase A 建议 |
|---------|------|-----|--------------|
| shiji | 史记 | history | 选录：本纪/列传高密度篇（如项羽、留侯、淮阴等） |
| zizhi_tongjian | 资治通鉴 | history | 选录：与进退、权柄相关卷目若干 |
| on_practice | 实践论 | epistemology | **全文优先** |
| on_contradiction | 矛盾论 | epistemology | **全文优先** |
| mao_selected_works | 毛泽东选集（官方1–5卷） | epistemology | **全文优先** |
| mao_selected_methods | 毛选方法篇选 | epistemology | superseded（由全书替代） |
| sunzi | 孙子兵法 | strategy | **全文优先** |
| the_prince | 君主论 | strategy | **全文优先**（中译需注明译者） |
| yan_tie_lun | 盐铁论 | policy_debate | **全文优先** |
| chuanxilu | 传习录 | cultivation | 选录：知行合一相关 |
| dao_de_jing | 道德经 | cultivation | **全文优先** |
| meditations | 沉思录 | cultivation | 全文或选录；注明译本 |

## 切块规则

1. **优先按自然结构**：卷 / 篇 / 章 / 目，禁止跨篇合并。  
2. **目标长度**：约 200–600 汉字（西书按词酌情）。  
3. **元数据**：`id, book_id, locus, text, prev_id, next_id, char_count`。  
4. **古文与今译**：若并存，分字段 `text`（据引用主文本）与可选 `text_modern`；默认引用锚定 `text`。  
5. **金句库**：`quotes/curated.jsonl` 每条含 `quote, book_id, locus, chunk_id, verified_by, date`；检索时可加权提升。

## Chunk JSONL 一行示例

```json
{"id":"on_practice-003","book_id":"on_practice","locus":"实践论·第二节","text":"……","prev_id":"on_practice-002","next_id":"on_practice-004","char_count":320}
```

## 版权与合规

- 只收录**公版**或你拥有明确使用权的文本。  
- 不把未授权商业电子书提交到公开 git remote；若需本地私有语料，加入 `.gitignore`（见仓库根或本目录 gitignore 约定）。  
- `META.yaml` 的 `license` 未填前，`ingest_status` 不得标为 `ready`。

## MANIFEST

Phase A 实现时维护 `corpus/raw/MANIFEST.md`：列出每书收录篇目、字数、就绪状态。当前占位见 `corpus/raw/README.md`。
