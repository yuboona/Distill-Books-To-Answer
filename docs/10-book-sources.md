# 书单与文本源盘点（Phase A 关口）

**当前步骤：** Phase A 第 1 步——冻结书单、锁定可合法使用且质量合格的文本源。  
**本地检索结论：** 磁盘上几乎没有可用原文；仅发现现代人《道德经直译》epub（**不推荐作底本**）。  
**公开源结论：** 多数书可找到 HTML/纯文本；PDF 可作为后备，但优先 TXT/HTML（免 OCR 噪声）。

质量标尺（本表）：

| 等级 | 含义 |
|------|------|
| A | 可直接入库：结构清、乱码少、出处明确 |
| B | 可用但需清洗：去导航/注疏噪音、分篇、或补标点 |
| C | 慎用：版本杂、OCR/异体多、版权或译本需再核 |
| F | 不入库：版权不明、今人二次创作、质量不可接受 |

PDF 原则：仅当无可靠 TXT/HTML，且 PDF 为可选中文字（非扫描糊图）时采用；扫描件需 OCR 验收后再定级。

---

## 总表

| book_id | 书名 | Phase A | 推荐源 | 格式 | 质量 | 备注 |
|---------|------|---------|--------|------|------|------|
| on_practice | 实践论 | 全文 | [Marxists.org 中文](https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-193707.htm) | HTML→txt | **A** | 抽检：关键句完整，CJK 干净；需剥页头注释 |
| on_contradiction | 矛盾论 | 全文 | [Marxists.org 中文](https://www.marxists.org/chinese/maozedong/marxist.org-chinese-mao-193708.htm) | HTML→txt | **A** | 同上；分节清楚 |
| sunzi | 孙子兵法 | 全文 | [维基文库](https://zh.wikisource.org/zh-hans/%E5%AD%AB%E5%AD%90%E5%85%B5%E6%B3%95) | HTML→txt | **A** | 抽检「兵者，国之大事」正确；文末附考需剔除或单置 |
| dao_de_jing | 道德经/老子 | 全文 | [维基文库·汇校版](https://zh.wikisource.org/zh-hans/%E8%80%81%E5%AD%90_(%E5%8C%AF%E6%A0%A1%E7%89%88)) | HTML→txt | **A/B** | 公版正文；勿用本地「直译」epub 当原文 |
| yan_tie_lun | 盐铁论 | 全文 | [ctext 盐铁论](https://ctext.org/yan-tie-lun/zhs) 优先；或 [维基文库四库本全览](https://zh.wikisource.org/zh-hans/%E9%B9%BD%E9%90%B5%E8%AB%96_(%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC)/%E5%85%A8%E8%A6%BD) | HTML/API | **B** | 四库本连写少标点、含提要注文；ctext 分篇更好 |
| the_prince | 君主论 | 全文 | [Gutenberg #1232 Marriott 英译](https://www.gutenberg.org/ebooks/1232) txt | TXT | **A**（英） | 公版英译质量稳定；中文须另找公版旧译或你自备已购译本 |
| meditations | 沉思录 | 全文 | [Gutenberg #2680](https://www.gutenberg.org/ebooks/2680) txt | TXT | **A**（英） | 同上；中文现代译多有版权 |
| shiji | 史记 | 选篇 | [维基文库·史记](https://zh.wikisource.org/zh/%E5%8F%B2%E8%A8%98) 分卷 | HTML→txt | **A/B** | 建议先收：项羽本纪、淮阴侯、留侯等；可用 ctext |
| zizhi_tongjian | 资治通鉴 | 选卷 | [维基文库·通鉴](https://zh.wikisource.org/zh-hans/%E8%B3%87%E6%B2%BB%E9%80%9A%E9%91%91) | HTML→txt | **B** | 体量大；Phase A 只选与进退/权柄相关卷 |
| chuanxilu | 传习录 | 选录 | [ctext 传习录](https://ctext.org/datawiki.pl?if=gb&remap=gb&res=152061) | HTML/API | **B** | 宜选「知行合一」相关条；注意版本 |
| mao_selected_methods | 毛选方法篇 | 严选 | Marxists.org 毛选中文栏目按篇 | HTML→txt | **B** | Phase A 可暂缓；先两论 |

---

## 本地已发现文件（质量裁定）

| 路径 | 判定 | 原因 |
|------|------|------|
| `~/0_系统性知识树/.../道德经直译1.1.epub` | **F（不作原文底本）** | 今人专栏式直译+架构比喻，非《老子》原文；且现代创作有版权风险。可作「延伸读物」但不进 `corpus/raw` 的 text 字段 |

未在 Documents/Downloads/Desktop 等处发现《史记》《通鉴》《实践论》《盐铁论》《孙子》等现成 txt/pdf 语料。

---

## 抽检摘要（本次已做）

| 源 | 抽检结果 |
|----|----------|
| Marxists《实践论》 | 含「通过实践而发现真理…」完整句；约 0.9万+ 汉字量级正文可用；页面有题注需剥离 |
| Marxists《矛盾论》 | 开篇「事物的矛盾法则…」正确；体量更大，结构可用 |
| 维基文库《孙子》 | 十三篇齐；名句正确；页脚考据文字需在 ingest 时丢掉或标 `appendix` |
| Gutenberg《君主论》Marriott | UTF-8 纯文本；章节标题清晰；含导言/附录，ingest 时应切「THE PRINCE」正文为主 |
| Gutenberg《沉思录》 | 纯文本完整；注意译本为旧英文，非梁实秋等中译 |
| 维基四库《盐铁论》全览 | 汉字量大、几乎无标点、夹提要/注文；**能用但清洗成本高** → 优先 ctext 分篇 |
| 维基《老子》汇校版 | 有独立页面；适合作文言底本 |

**关于 PDF：** 网上有「五篇哲学著作」等 PDF，但来源站点杂、排版/OCR 不一；在已有 Marxists HTML 时**不必用 PDF**。扫描版 PDF 一律先 OCR 抽检后再定级，默认不优于 HTML。

---

## 版权与合规提醒（入库前必读）

1. **先秦两汉及多数古注公版正文**：维基文库 / ctext 常见可用；仍须在 `META.yaml` 写明 edition。  
2. **《实践论》《矛盾论》**：马克思/毛著网络文本流通广（Marxists.org）；个人学习语料常见做法是收录并注明来源 URL；若日后公开分发仓库，再核对你所在法域要求。  
3. **《君主论》《沉思录》**：Gutenberg **英译公版**最省事；若坚持中文引用，需自备版权清晰译本（勿从网盘随意扒今译）。  
4. **ctext API**：批量拉取可能需 API key / 遵守使用条款；Phase A 可先手工导出分篇 HTML。  
5. **禁止**把未授权商业电子书、今人译注 PDF 直接 commit 到公开 remote。

---

## Phase A 建议冻结清单（先做这些）

**立刻可抓（A 级优先）：**

1. 实践论（Marxists）  
2. 矛盾论（Marxists）  
3. 孙子兵法（维基文库）  
4. 老子/道德经（维基汇校）  
5. 君主论英译（Gutenberg）  
6. 沉思录英译（Gutenberg）  

**第二批（B，需清洗/选篇）：**

7. 盐铁论（ctext 分篇）  
8. 史记选 3～5 篇  
9. 通鉴选 2～3 卷情境  
10. 传习录选「知行」相关  

**暂缓：** 毛选其它篇（等两论管道跑通）。

---

## 你确认后的下一步

1. 你点头「按冻结清单抓取」→ 我写入 `corpus/raw/<book_id>/` + `META.yaml` + `MANIFEST.md`（清洗导航与附录）。  
2. 然后实现 `scripts/ingest.py` → chunks。  
3. 再实现 `retrieve.py` / `verify_quotes.py`。

若你希望**全文只用中文**，请说明：君主论/沉思录是否接受英译作 Phase A 过渡，或你提供已购中译文件路径。
