# 文档解析边界与纪律（ontology-ingest parsing-limits）

> **本文件=格式解析边界与工程纪律的唯一迭代入口**（防堆砌纪律，照 model reasoner-limits / review presentation-discipline 先例）：新解析边界、许可登记、确定性纪律一律进本文件；SKILL.md 只留阶段/闸门/铁律/指针，不叠加条款。
> **编号稳定**：限制编号 ①-⑱ 为全链稳定引用位（tpl-extract-pack / parse_documents.py 注释 / CHANGELOG 按此引用）。修订内容不改编号；废止保留编号标「已废止+替代」，编号不复用。
> **架构**：LLM 整页布局感知转录 primary + 机械渲染/inventory/substrate/交叉校验护栏；质量目标=**萃取就绪的保真**（S1 能消费的保真），ingest 产物与 model S1 消费按唯一接缝契约 `../../ontology-model/references/s1-handoff-contract.md` 共同设计。
> 子协议版本（pack schema 2.1 / page-transcribe 1.1，additive 向后兼容）独立登记不联动，见 `assets/tpl-extract-pack.md`。

## 一、格式解析边界（逐格式）

- **① PDF 文本层（inventory 非最终正文）**：pypdf `extract_text()` 抽文本层→**完整性 inventory**（ground truth，I3 交叉校验防 LLM 漏字），**不作最终正文**。表格/视觉结构由 **LLM 整页转录重建**（渲染图→布局感知 md）。中文文本层需源 PDF 嵌入 CJK 字体方可抽取；无文本层→image-only 页（⑬）。**每页 pypdfium2 渲染 PNG 交 I2，无静默跳过**。
- **② PDF 加密**：RC4 加密纯 Python 可解（`decrypt(password)`）；**AES 加密需 cryptography**（pypdf[crypto] 可选 extra，默认未装）→`DependencyError`→exit 2+提示 `pip install pypdf[crypto]`，不崩溃。密码错→exit 2。
- **③ 扫描页/图片型页（整页渲染 primary）**：pypdfium2 渲染**每一页**→PNG（无论有无文本层）→I2 整页布局转录。image-only 页（无文本层）inventory.items=[]，完备性靠整页渲染呈现+IG1 目视（⑬）。pypdf `page.images` 直提路径退役（渲染已覆盖全视觉；页内多图/矢量叠加直提不完整）。
- **④ Word（结构化 substrate + inventory + 内嵌图导出）**：python-docx 结构化转换（Heading N→#/Title→#/列表 numFmt〔style 名 List Bullet/Number + numPr 兜底〕/行内加粗斜体按 run/表格合并去重 `c._tc is prev`）→**精确文本 substrate**（直抽比 OCR 更准）；段落+表格单元格→inventory；**word/media 内嵌图导出** attachments→I2 转录（DOCX 内嵌图表路径）；LibreOffice 可用时渲染页图作布局参照（可选）。`core_properties.created` 常模板默认值（2013 假日期）→doc_date 警示 gap。LLM 复核 substrate 结构 + 转录内嵌图。
- **⑤ Excel（单元格 substrate + inventory）**：openpyxl 每 sheet→单元格网格 md substrate（**合并保留归左上+注记/多行单元格 `<br>` 保全/公式双读** data_only=True 缓存值 / False 公式文本，无缓存→录公式+gap formula-no-cache/日期 ISO/数值照录）；非空单元格→inventory；嵌入图导出 attachments。LibreOffice 可用时渲染 sheet 图作布局参照（可选）。**LLM 语义重组为 headed 表**（按业务语义分组）＝结构重建**非 OCR**（防网格碎片化/节标题混行/尾部空行）。
- **⑥ PPT（位置 substrate 保结构）**：python-pptx **位置 substrate**——每 shape 边界框 bbox（EMU→英寸 x,y,w,h）+文本+类型+表格+图片引用，**按视觉位置 (top,left) 排序**，组合 shape 递归一层；备注页→inventory（专家口述权威信号）；嵌入图导出 attachments。LLM 据 bbox 重建分组小节（四象限/多栏）重建 md 列表。**项目符号机械映射（无需渲染）**：业务 PPT 项目符号常是文本框字面符号字符（Wingdings/Symbol 字体 run，非程序化 buChar），`run.font.name` 识别符号字体，**引导短符号 run（码位如 0x75「u」渲染■）→列表前缀「- 」**（视觉即项目符号，结构重建非臆造），行内符号 run（多为空格 0x20）原样保全；无符号字体时与 `p.text` 字节等价（`_pptx_para_text`，双跑确定性）。**LibreOffice 可用时渲染幻灯片 PNG 作全视觉保真增强**（可选，跨平台）；无 LibreOffice→位置 substrate（含机械列表前缀）+ 内嵌图供 LLM 布局重建（**纯 pip 无头确定性主路径，结构保真不依赖渲染**）。chart→gap embedded-object。
- **⑦ 图片（原图直供 LLM 整图转录）**：PIL 元数据（format/size/mode）；二进制副本 attachments+sha→**rendered_image 直供 I2 整图布局转录**（多列 x 坐标分区/水印剔除/OCR 误读核对）；EXIF 日期→doc_date 候选（doc_date_source:exif）。inventory.items=[]（⑬ 诚实边界）。每图 rendered_image+prepared（必过 LLM）。
- **⑧ OCR（LLM 整页转录 primary）**：**多模态 LLM（I2 page-transcribe agent）是一切视觉内容的通用转录权威**（PDF 页/幻灯片/图片/内嵌图），整页布局感知重建。tesseract 等系统 OCR 二进制不引入（违通用性 + 与既有 vision agent 冗余）；可选 macOS Vision OCR（swift 桥）作图片 inventory assist（平台特定，OCR 有误读，非硬保证，⑬）。本地 VLM（olmOCR/dots.ocr/MinerU AGPL/Marker GPL）不引入（重 deps + 跑第三方模型 + 许可不兼容）。

## 二、许可与依赖（MIT 套件纯净）

- **⑨ fitz/PyMuPDF 零代码路径（pypdfium2 替代）**：PyMuPDF=**AGPL-3.0 或 Artifex 商业双许可**（copyleft 强于 LGPL，import 即运行时链接 copyleft，MIT 套件污染争议）。**连可选 import 都不写**。**PDF 渲染用 pypdfium2**（BSD-3-Clause OR Apache-2.0，MIT 兼容，纯 pip wheel 自带 pdfium 二进制）替代 fitz 栅格化。poppler（pdf2image 后端）=系统二进制不引入。fitz 套件代码零引用。
- **⑩ 解析/渲染库许可（全链无 copyleft，dist-info METADATA 实证核验）**：

  | 依赖 | 实证版本 | 许可 | 角色 |
  |---|---|---|---|
  | pypdf | 6.14.2 | BSD-3-Clause | PDF 文本层 inventory |
  | **pypdfium2** | **5.11.0** | **BSD-3-Clause OR Apache-2.0** | **PDF→页图渲染（wheel 自带二进制）** |
  | python-docx | 1.2.0 | MIT | Word substrate/inventory |
  | openpyxl | 3.1.5 | MIT | Excel substrate/inventory |
  | python-pptx | 1.0.2 | MIT | PPT 位置 substrate/inventory |
  | Pillow | 11.3.0 | MIT-CMU | 图片元数据/解码/PNG 编码 |
  | lxml | 6.1.3 | BSD-3-Clause | 传递（docx/pptx） |
  | et-xmlfile | 2.0.0 | MIT | 传递（openpyxl） |
  | typing_extensions | 4.16.0 | PSF-2.0 | 传递（pypdf py<3.11，CI 3.9 矩阵） |
  | XlsxWriter | 3.2.9 | BSD-2-Clause | 传递（pptx 硬依赖） |
  | **LibreOffice**（可选） | 系统安装 | **MPL-2.0** | **office→PDF 渲染（独立子进程，不污染 MIT；brew install --cask libreoffice）** |

  六直行 pip 依赖入 `requirements.txt` 精确钉住（+pypdfium2）；传递依赖不入 requirements 但登记 `THIRD-PARTY-LICENSES.md`。LibreOffice 是**可选系统前置**（独立子进程调用，MPL-2.0 文件级 copyleft 不感染 MIT 套件代码），无则 office 退 substrate-only（纯 pip 主路径仍工作）。**版本敏感**：输出字节稳定性按实证版本登记，升级须重跑双跑确定性。pypdf[crypto]（AES）可选 extra 默认未装（②）。**pypdfium2 安装须 --only-binary=:all:**（旧 pip 选 sdist 会触发 GitHub 下载 pdfium 二进制超时；wheel 托管 files.pythonhosted.org 可达）。

## 三、确定性纪律

- **⑪ canonical 零时间戳 + 同源字节→同包字节 + 渲染双跑字节等**：canonical 准备态包（MD+manifest）零 now()/零 mtime/零随机 id；sections/gaps/term_candidates/attachments 全排序；pack_id 内容哈希；`json.dump(sort_keys=True, ensure_ascii=False, indent=1)`+尾换行；MD LF。**PDF→PNG 渲染双跑字节等**（pypdfium2 实证：同 PDF 字节+scale→同 PNG sha）；office substrate 确定性（python-docx/openpyxl/python-pptx 直抽）。**契约=同源字节→同包字节**——Office 保存字节跨次不稳是源件属性非解析器缺陷（fixture 一次生成解析两次，断言全量字节等）。**LibreOffice 渲染若启用可能嵌创建时间戳→登记为非 canonical 中间层**（渲染图 sha 登记，canonical 双跑断言 scope 机械 inventory/substrate/manifest；LibreOffice 渲染确定性须单独验证或剥离 PDF 元数据）。时间戳只在 transcribe_meta（I2 回填后非 canonical 层）。源 sha256 前后断言零回写；realpath 碰撞守卫；再解析守卫护转录层。

## 四、term 种子与 hint 边界

- **⑫ term_candidates 结构种子（零 NLP）**：章节标题串+表格首行单元格串+substrate ATX 标题串（DOCX 标题在 substrate，source=heading|table-header|substrate-heading），freq=全包精确匹配计数。**不做中文分词**（jieba/pkuseg 未实证=scope creep；裸 n-gram 噪声违零臆造精神）。覆盖率低于分词→S1 主会话按「≥3 次名词强制登记」补全，脚本不越权萃取。semantic_hint 机械启发式多标签可为空 []、永不权威（tpl §四），S1' 第1步逐节复核。

## 五、保真与接缝边界（续编号）

- **⑬ image-only 完备性诚实边界**：image-only 页/图片（无文本层，inventory.items=[]）→**机械无法比对 LLM 是否漏转录图内容**（无 ground truth）。保证＝**整页渲染图必呈现给 LLM（无静默跳过）+ IG1 用户目视复核**（对照源件）。可选 macOS Vision OCR（swift 桥）提供图文字 inventory assist（平台特定，OCR 有误读，登记为 assist 非 ground truth，不硬绑通用性）。**不伪称机械保证 image-only 完备**——诚实登记边界，人核兜底。
- **⑭ LLM 转录成本与规模（质量优先 tradeoff）**：每视觉单元一次 LLM 整页转录，成本显著高于纯机械提取。**质量优先**（不局限 pip/成本）。批处理优化（按文档/小批页 agent 返回数组）为后续优化项，非默认。大规模文档集 LLM 调用成本须 run-manifest 诚实登记。
- **⑮ 机械/LLM 分界（纪律保留）**：**机械产准备态护栏（渲染/inventory/substrate），LLM 产最终清洁正文 primary**。分界纪律不塌陷：机械 CLI 不调 LLM（canonical 准备态）；LLM 经只读 agent（零臆造）；I3 交叉校验机械（inventory 覆盖断言，护栏非权威，缺失登记 gap 供人核不自动改 LLM 转录）。**不变量：任何单元都不被静默路由 mechanical-only 跳过 LLM**。清洁 md（机器元数据全入 manifest，正文无机器锚）防下游 S1 污染。
- **⑯ 图样保真二分 + 形态分类 fail-safe**：清洁 md 呈现按形态二分——**图样类**（flow-diagram / ui-interaction / architecture-diagram / chart）**嵌原图 `![[attachments/...]]` + 「图内文字照录」节**（节点文字/箭头条件/标注/泳道标题/轴标签，带轻量区域归属），**绝不拍平成「有序步骤列表」叙事**（拓扑〔分支/并行/泳道/时序〕是 BPMN2.0/OWL-S 流程语义的直接载体，文字化扁平化丢失，**拓扑解读留 S1 Read 原图提炼**——那是「义」S1 领地，ingest 只保「形」+ 照录图内文字）；**文字类**（text-prose / table）纯文本转录**不嵌原图**（清洁 md 对 RAG 友好、对 S1 不冗余，原图仍在 attachments 兜底 S1 需要可回看）；装饰 not_transcribed。**形态分类 unit_type 是 LLM 整页转录副产品**（机械分不了形态——pypdf/openpyxl 只知「有无图/文本密度」，分不清流程图 vs 文字表），**fail-safe 不承重**：机械层无条件保图（attachments + manifest 指针完全不依赖分类），分类只驱动清洁 md 呈现不驱动图是否存在，误判可恢复（流程图误判文字类→S1 拿原图重解读拓扑；内容图误判装饰→IG1 人核对照源件兜底），拿不准保图保守（other/mixed 嵌原图 + 照录可读文字 + flag uncertain），唯一真正剔除的是高置信装饰（not_transcribed 登记 reason 可审计）。**图样拓扑语义只在多模态消费可得**（纯文本/RAG 消费拿不到分支/并行结构，下游须知）。原图取最高保真载体（内嵌图原件 pictures 优先，否则整页渲染图）。详见 s1-handoff-contract §一/§二。
- **⑰ 接缝元数据 + 溯源映射**：manifest section 增四类 **I2 回填 affordance**（准备态 null/[]，机械层不裁定）——**unit_type**（形态维，与 semantic_hint 内容特征**正交**：形 vs 义）/ **verification_status**（置信度三值 substrate-exact〔机械精确底 LLM 只结构重建〕/ render-transcribed〔渲染 + inventory 交叉校验〕/ image-only-transcribed〔无 ground truth IG1 人核兜底〕，I2 按 substrate_used + inventory.items 设，S1/G1 校准怀疑度——image-only + uncertain 单元更怀疑，不对所有内容一视同仁）/ **personal_info_regions**（个人信息精确位 `[{region, kind:人名|证件号|联系方式|机构名歧义, reading:照录原文}]`，**登记位非脱敏**〔照录不脱敏纪律不越界〕，给 S2 精确脱敏 checklist 非全文猜；水印个人标识仍进 not_transcribed 不进本字段）/ **md_heading**（LLM 清洁 md 实际语义标题，桥接 section_id↔清洁 md 节——PDF 机械 heading 是页号「第 N 页」非语义，须 md_heading 桥接非纯 positional）。**溯源链** `source(doc_id+sha) → section(section_id+locator+md_heading) → 描述句(tpl-29「来源」列) → TTL(rdfs:isDefinedBy/skos:note annotation)`，是方法论 methodology-core §1.2「事理层知识要求可登记来源」的字段化落地（**可持续维护命门**：产品参数变更时定位受影响 TTL 公理，G1 回溯源页核验/S4 审计引源/S6 黄金用例溯源）。I3 收卷断言节序↔manifest 一一对应 + md_heading 落位 + verification_status 汇总 + personal_info_regions 齐。详见 s1-handoff-contract §三/§四/§五。
- **⑱ PPTX 原生矢量图样保图边界**：⑯「机械层无条件保图」覆盖 **raster 载体**——内嵌图原件（pictures，pypdf/python-pptx 只导出 raster）+ 整页渲染图（rendered_image，pypdfium2/LibreOffice）。**PPTX 原生矢量图样**（GROUP 组合/矢量箭头/连接符，非 raster 内嵌图）在 **substrate-only 档**（LibreOffice 未装或 `--no-office-render`，无整页渲染）下**无图片载体**（pictures 不含矢量 shape，rendered_image=null）——「S1 拿原图重解读拓扑」fallback 对此类单元**不闭合**。**内容仍不丢**：python-pptx shape substrate（文本+bbox）承载节点身份/编号/位置，S1 消费 substrate 位置结构重建拓扑（接缝契约 §六.2 **联合消费**：Read 原图给关系 glyphs〔方向/连接符/节点形态〕+ substrate 给节点身份〔编号/标签照录，身份权威〕），**IG1 目视源件兜底**。fail-safe 不变量「形态分类错误绝不造成不可逆内容丢失」仍成立（substrate 保内容）；但「原图视觉重解读」承诺对原生矢量 substrate-only 档不闭合，**诚实登记为边界非静默丢失**。**可选增强（非默认）**：图样类单元整页渲染兜底（LibreOffice 可用时 render 原生矢量→PNG，恢复 Read 载体）；矢量导出（pptx→svg）为后续扩展位候选。详见 s1-handoff-contract §1.2 澄清 / §九。

## 六、完整四通道扩展位（无排期承诺）

> 完整四通道愿景：talk（ASR 音频转录）/ code（SQL DDL/ORM schema/API spec 实体-关系-约束提取）/ diagram（BPMN XML 优先直解析 + 多模态识图）/ data（DB metadata 列 profiling + 样本值 + 关系推断，专有 DB 连接器）。本地专有服务依赖部分外接，不进当前 CLI。启用条件=消费场景硬需求。

- 分词库（term 候选增强）/ ASR 服务 / DB 连接器（可复用 MCP 客户端模式，专有绑定时须通道中立化）/ 批处理转录优化（⑭）——均留后续评估。pdfplumber/tesseract 已不再需要（LLM 整页转录覆盖表格/OCR，①⑧）。
- 四通道预留扩展位：届时 ingest 内增通道 handler（talk/code/diagram/data），pack schema 升版登记，CLI ingest group 增 action。
