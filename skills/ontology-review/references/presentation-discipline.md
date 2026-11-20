# 呈现纪律（ontology-review R2 规范性条款）

> **本文件=审阅页呈现规范的唯一迭代入口**（防堆砌纪律）：新呈现规范、条款修订、实验性呈现规则一律进本文件；SKILL.md R2 只留命令、七区概述与指针，不叠加条款。
> **编号稳定**：条款编号（①②③④⑤⑥⑦及 b/c/d/e 后缀）沿用 R2 前缀，为全链稳定引用位——`scripts/self_test.py` E8/E10 按此断言，模板 `assets/review-page-template.html` 与 CHANGELOG 按此引用。修订条款内容不改编号；废止条款保留编号并标注「已废止+替代条款」，编号不复用。
> 消费方：build_review_page.py / review-page-template.html（实现）、self_test.py（机械回归）、专家审阅反馈（条款来源，轮次映射见 CHANGELOG C 节）。

## 信息分层

- **② 类与属性按继承根分组**：组内先序（父类在前、子类缩进标「第 N 层」），不平铺；属性表列 = 属性名（原文含中文名）· 类型/取值 · 约束要点 · 消费级 + md 额外列
- **②b 层级缩进可视化**：30px/层缩进 + 左侧层级色条 + 标题 `↳` 前缀 + 「上级：父类中文名」
- **⑤b 规则三层呈现**：第 1 层 md 业务陈述（建模方案原文）→ 第 2 层「通俗逻辑」= `plain_swrl()` 确定性模板翻译（**不过 LLM**，保机械回归纪律）→ 第 3 层 SWRL 结构 `<details>` 默认折叠（工程师核对用）
- **③b 长表截断折叠不分页**：长文本列 3 行截断 + title 悬停全文；超 N 行折叠 + 展开按钮——审阅常需上下行对照，分页切断对照；折叠不丢信息可打印全量

## 主题归组

- **⑤ 同业务编号的编译变体合并为一张卡**：卡内逐条列变体并标「引用通道/字面量展开通道」
- **⑦b 同构件多条批注**：弹窗顶部列该构件全部既有批注（逐条编辑/删除），表单默认新增态；编辑态显式提示「保存将覆盖该条」——单条覆盖模式不满足专家多意见场景

## 记法与交互

- **③④ 宽表横向滚动**（`.tbl-wrap`），窄屏不撑破页面；③ 列按 md 实际表头动态生成（跨 run 列数不同）
- **③b 批注列 sticky 右置**（`th/td.stick`）：无需横向拖到最右即可点批注
- **⑥ 空定义显式标注**「⚠ 词典未定义」（不静默显示「—」），并给批注入口
- **⑦ 批注反显**：再次点选同一构件 → 弹窗回填已存意见/建议/严重级并进入编辑态（保存为覆盖，不重复登记）；已批注构件按钮显示「已批注 N」；⑦ 区支持「定位/编辑/删除」
- **⑦c 双时间戳**：`ts` 存 ISO（机器消费）+ `ts_local` 北京时间字符串（人读，`Asia/Shanghai`）；导出 JSON 双字段，旧数据无 `ts_local` 时前端 `fmtBJ(ts)` 现算兼容

## 图示升级（D2，六板块；1.3.0 新增）

> 七区中①类图原为唯一 cytoscape 图示，其余六区为结构化表格——业务专家须在表格间人脑拼接逻辑链。D2 把六板块升级为图示（读），与 D4 拖拽编辑（写）共建图交互层。全部图示复用既有 cytoscape+dagre vendor（**禁新增 vendor**），新 JS 一律并入末个 app script 块。数据供给来自 review_extract `supply` 顶层键（R1 扩展，schema_version 1.1）；legacy review.json（无 supply）→ 各图显式「数据层未升级」hint，不静默空图。

- **①b 类继承树可折叠**：①区既有类图升级——子树折叠/展开（BFS sub 边隐藏后代 + dagre 重布局）+「全部展开/收起」工具条；tap 节点详情不变；derived 虚框保留。cy 句柄提升入 `GRAPHS.classes`（见模板硬约束）。
- **③c 属性域值域图**：③区表上方新容器——类节点 + 属性矩形节点 + union 枢纽节点（`u:<prop>:domain|range`）；dagre LR；tap 属性节点→侧面板详情（D4 L1 入口）。**union 收编**：`domain_union`/`range_union`（1.2.2 确定性修复已在位）经枢纽节点渲染，匿名值域成员可见——「待迭代观察项」union 共享属性呈现由此闭环（数据零新增提取，仅渲染）。
- **④b 公理族约束图**：④区表上方——渲染 `axiom_graph`（TTL OWL 公理构件提取：Restriction/AllDisjointClasses/equivalentClass/hasKey/characteristics/inverseOf/datatypeFacet/oneOf；**content-derived 节点 id，禁 bnode 随机标签**；owner 经反向 BFS 回溯具名类）；节点形状按 kind 区分；tap 约束节点→侧面板列 md_overlay 公理行 + 批注；`md_only`（无 TTL 构件承载的 md 公理行）显式「应用层/md 承载（无 TTL 构件）」不静默。**④区标题「七族」→「约束六族」+ hint「R 推导族见⑤区」**（SKILL R1 明示七族=约束侧六族+R 推导族，R 推导已在⑤规则区呈现；famNames 六族 F/L/C/P/X/S 不动）。
- **⑤c 规则流图**：⑤区卡上方——节点=规则枢纽（`r:<rid>`）+ atom 节点（`a:<atom_id>`，body 蓝/head 绿，label=renderAtom）+ 变量节点（`v:<name>`，跨规则同名合并）；边=枢纽→body（cond 标①②③序）/枢纽→head（concl）/atom→var（bind）；字面量实参内联 atom label 不出节点；dagre LR；tap atom→侧面板 + 批注（kind=rule, id=md_key, anchor）。数据来自 `atom_meta`（atom_id 位置派生 `<rid>.b<i>`/`.h<i>`，跨 parse 确定）。
- **⑥b SKOS 层级图**：⑥区表上方——`broader_list` child→parent 多父边（g.objects 多父通用实现，fixture 0 多父为森林）；`definition_missing` 虚框琥珀；dagre TB。
- **⑦d 批注图锚点**：opinion 可选 `anchor={graph,element}`；openModal/saveOpinion 携带（`data-anchor-graph`/`data-anchor-element` 委托）；`jumpTo` 扩展 `jumpToGraph`（滚至区→`GRAPHS[graph].getElementById`→animate center+闪烁）；**legacy 无 anchor 回退 DOM `cls-`/`rule-`**（renderOpinions 保留）；markAnnotated 扩展图元素 `.annotated` 绿框反显。

## 拖拽编辑（D4，L1-L2 TBox；1.3.0 新增）

> 审阅与修改原分离承载（意见走入口 (c)），专家无法在页面直接做轻量形式化编辑。D4 加 L1-L2 拖拽编辑（写）：**前端产 patch JSON（channel=d4）→ 外接编排器跑 R2 CLI 机械执行 + L1/L2 校验 → draft 非权威 + report → 入口 (c) S4 晋升**（路径甲）。保单文件 HTML 零依赖离线铁律（禁 pyodide/WASM/CDN）；R2 引擎零改动；实时性=提交时 CLI 校验，非浏览器秒级预检。**浏览态行为零回归**（批注/导出意见不变）；D4 草稿态独立 localStorage（`STORE_KEY+"-d4"`，旧意见数据零碰撞）。ABox 实例值编辑 + L3 规则编辑延后。完整导出契约见 `assets/tpl-d4-patch-schema.md`。

- **②c L1 侧面板编辑**：编辑态复用 `aside#side`——label input / comment textarea / 枚举 chips；before 取 `literal_meta` 精确 `{value,lang,datatype}`；comment 缺失→add_triple 路径；**G8 禁用 chip**（`enum_editable.editable=false` 灰显 + tooltip 转入口 (c)，oneOf 重名不可消歧）；保存→stage + 节点/行 pending 徽标 + cy label 预览；逐条可撤销。**target 白名单=class/object_property/data_property（排除 rule/skos）**——MAJOR 陷阱：rule 目标 label 编辑→diff s=swrl:Imp→rule_touched→MAJOR 须 golden 守护，L1 轻量编辑不得触发。
- **①c L2 拖节点改 subClassOf**：编辑态 grabify；dragfree 命中测试落点类节点→确认弹窗→stage subclass 编辑 + 预览重绘。**parents_guard 守卫表**：恰 1 具名父 + 0 匿名父→reparent（remove+add）；0 具名父（根类）→add-only 加父；>1 具名父或匿名父>0 且涉删→禁用转入口 (c)（G4 匿名表达式 R2 不可寻址）；环检查（新父祖先闭包不含自身、新父≠自身、双方具名类）。
- **③d L2 拖边改 domain/range**：cytoscape 3.30 核心无边端点重连——编辑态 tap prop 边→生成 2 临时 handle 节点（grabbable 方块 + 虚线临时边），dragfree 命中类节点→确认「domain/range X→Y」→stage；**union 边 handle 禁用**（匿名值域转入口 (c)）；仅具名 domain+range 的 `e-op-*` 边可编辑。**无障碍回退**：tap 边→侧面板 domain/range 双下拉（同语义同 ops）。
- **⑦e D4 patch 组装导出**：复用 export Blob 先例——patch JSON `schema_version 1.0` / `channel=d4` / **patch_id 内容哈希**（`P-d4-`+sha256(canonical({baseline,operations}))[:12]，同编辑→同 id→draft 双跑字节等）/ `baseline.sha256=sha256_full`（64hex）/ operations 全 IRI + 字面量 dict 全等编码。**串行纪律**（一次一个待导出，exported 锁定，基线刷新后新会话，sha 错配→引擎 exit 2→重审提示铁律 5）。**report 回读离线闭环**：`<input type=file>` FileReader 读 patch-report.json→渲染 verdict/version.bump/diff.named_summary/blocked_reasons/validation.l1_l2.new_errors/regression.verdict/zero_writeback；**blocked draft UI**（exit 1 仍产 report）→修复指引 + 入口 (c) 提示。**编排器序列文档化**（浏览器不跑 CLI——G6）：review extract→page→D4 编辑→export patch.json→`ontology_cli.py model patch … --golden … --output-draft <工作区> --report <工作区>`→晋升前终检 --regression-full→report 回读→入口 (c) S4 审计→G2/G3→人工晋升→重跑 extract/page 复核（round-trip）；输出落工作区 cwd 不进 run 目录（R2 零回写）。**回读文件类型守卫**（用户验收修复，1.3.0 发布前）：`verdict` 字符串→报告渲染；`operations+patch_id` 无 verdict→补丁预览（opDesc 逐条）+「这是补丁不是报告」提示+产报告 CLI 命令（误选 d4-patch.json 不再静默 `?`）；其余→「无法识别」引导。回读区只读引擎报告，浏览器不跑 CLI（路径甲）。

## plain_swrl() 角色定名算法契约（⑤b 第 2 层，零占位符硬要求）

- 三遍角色定名优先级：body ClassAtom 类中文名（权威）> 对象属性第二参 range 类名 > 数据属性第二参「属性名+值」> 兜底「对象」
- 首现「某实体」/回指「该实体」；同名多变量甲乙消歧
- **head ClassAtom 不参与角色定名**（结论类不得篡夺主语角色）；回指且角色==类名的 ClassAtom 句省略（冗余）
- 句中不得残留原始变量名（vR1_a 形态）或占位符（?N/?v 形态）——角色名词代入后专家零对照成本（E10 断言）
- **vars 图例非空**（1.3.0 一行修）：`plain_swrl()` 返回 `vars=role`（角色定名 map 本就存在，原 `vars:{}` 丢弃致图例恒空）；模板 plainOf 渲染 `p.vars` 立即生效；body/head 串逐规则全等（E10 安全），plain_swrl 仅 merge 调用、签名取 parse_ttl rules 不取 plain→T4 安全

## 模板实现硬约束

- **CSS 特异性**：缩进规则须 `.rulecard.depth-N` 提权，否则被后方 `.rulecard{margin}` 同特异性覆盖
- **任何覆盖 display 的样式不得挂在 table/tr/td 结构元素上**：line-clamp 依赖 `display:-webkit-box`，截断必须挂 td 内层 div（`.tbl-wrap .clip`）——直接挂 td 会覆盖 `display:table-cell` 破坏表格网格（内容纵叠/表头错位）
- **GRAPHS 注册表**（D2/D4）：`const GRAPHS={}`，①区局部 cy 提升为 `GRAPHS.classes`，各板块 IIFE 注册（`GRAPHS.props`/`GRAPHS.axioms`/`GRAPHS.rules`/`GRAPHS.skos`）；元素 id 图内命名空间，锚点={graph,element}；cytoscape-dagre compound 限制→扁平节点设计（无 compound），规则枢纽路由代 body→head 直连
- **print 回退**（D2）：`@media print{nav,.side,#cy,.graph-box,.d4-ui{display:none} .print-only{display:block}}`；每图配 `.print-only` 边表/层级列表（渲染期生成，信息不丢）
- **单 app script + E9 逐块**（D2/D4）：新 JS 一律并入末个 app script 块（vendor 三块在前）；self_test E9 `blocks[:3]`=vendor 跳过、`blocks[3:]` 逐块 node --check（修原只查末块盲区）；E8 断言模板 script 块数==4（防 vendor 槽位移）

## 待迭代观察项

| 观察项 | 现象 | 状态 |
|---|---|---|
| union 共享属性呈现 | 匿名 union 值域（domain_union/range_union）的共享属性不在各成员类卡片显示（parse_ttl 确定性修复前后行为等价，非回归） | **已收编③c（1.3.0）**——属性域值域图经 union 枢纽节点渲染匿名值域成员，数据零新增提取（1.2.2 已在位）仅渲染；行保留编号稳定 |
| 大图性能 | 6 cytoscape 实例（D2 全板块）真实大本体渲染成本 | 登记待迭代——fixture 小不阻塞；可选 nav 懒初始化（post-MVP），不阻塞现行条款 |