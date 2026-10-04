# 07 · 与 Cursor Skill 对接

> 产品目标：**元 skill**（建库 + 答问）。完整目标见 [13-meta-skill.md](13-meta-skill.md)。

## 两端分工

| 端 | 路径 | 职责 |
|----|------|------|
| Skill | `~/.cursor/skills/shi-shi-qiu-shi/` | **Mode BUILD + Mode COUNSEL** 入口、七步、禁令 |
| 本项目 | `05-shi-shi-qiu-shi/` | 语料实例、脚本、规范真源 |
| 用户 corpus | `corpus/` | BUILD 产物；**不**随 skill 分发 |

`skill-bridge/`：操作卡（探测 → BUILD 或 COUNSEL）。

## Mode BUILD

无 `ready` 书、无 chunks、或用户要求建库：

1. 确认/生成 `BOOKLIST.yaml`  
2. bootstrap → fetch/import → clean → META  
3. `ingest.py` → chunks  
4. smoke retrieve + verify  
5. 成功后再允许 COUNSEL 引典  

## Mode COUNSEL

1. 探测 corpus：无 ready → BUILD 或 L0，不假引典  
2. Pass-1：`retrieve.py --query "<原问>"`  
3. 繁体/英文书或 `low_confidence` → 模型改写查询（权宜，见 [12 §3.6](12-script-language-retrieval.md)）→ Pass-2 `--extra-queries`  
4. 只根据 pack 起草（改写句不得进「原文依据」）  
5. `verify_quotes.py`；PASS 输出 / FAIL 降级  

## Skill 状态

- [x] 双模式写入个人 `SKILL.md`  
- [x] 无库不引典；有库必须检索+校验  
- [x] bridge 与 [13](13-meta-skill.md) 对齐  
- [x] 脚本/docs 物理并入 skill 包（Phase M2） — `python3 scripts/pack_skill.py`  

## skill-bridge

见 [../skill-bridge/README.md](../skill-bridge/README.md)。
