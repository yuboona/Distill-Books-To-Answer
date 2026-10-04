# 双语书检索与回答协议

适用于：`the_prince`（君主论）、`meditations`（沉思录）。

## 目标

- **检索正确**：命中英文底本中的真实句子。  
- **回答中文**：分析、方略、七日动作全部中文。  
- **不造假中文原文**：禁止写「马基雅维利原文曰：『……』」却塞进自拟中文。

## 推荐输出形态

```markdown
## 原文依据
1. 《君主论》CHAPTER XVII（Marriott 英译）：
   > Upon this a question arises: whether it be better to be loved than feared...
   （意译：是否爱戴优于畏惧……——意译非原文）

## 据文分析
（中文）

## 方略
（中文；权术类必须含「不可做」红线）
```

## 检索提示（给 Router / retrieve / Skill）

当用户用中文问权力/畏惧/新主/同盟等问题时：

1. 先用下表做确定性扩词；  
2. 表未覆盖或英文书弱命中时，**Skill 驱动模型**把简体问题改写成 1–3 条英文检索短句 + 关键词，经 `--extra-queries` 再检；  
3. 改写只为检索，**不得**当马基雅维利中文原文。

| 中文意图 | 英文检索词示例 |
|----------|----------------|
| 被人爱还是怕 | loved feared cruelty clemency |
| 新岗位站稳 | new principalities own arms fortune |
| 同盟背刺 | auxiliaries mercenaries faith |
| 声誉与实力 | reputation arms |

`meditations` 同理：controllable, opinion, duty, obstacle 等。

细则与触发条件见 [12-script-language-retrieval.md](12-script-language-retrieval.md) §4.3。

## 与生成总协议关系

本文件是 [05-generation-protocol.md](05-generation-protocol.md) 与 [12-script-language-retrieval.md](12-script-language-retrieval.md) 的补充。冲突时以「英文原句作依据 + 中文作答」为准。
