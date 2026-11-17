# 第三方组件许可声明（THIRD-PARTY LICENSES）

> 套件自身代码以 MIT 许可发行（见 `LICENSE`）。本文件登记**随套件捆绑分发**的第三方组件及其许可，
> 以及**不捆绑、经 pip 单独安装**的运行依赖许可注记。
> 版本锁定与哈希明细见 `skills/ontology-review/assets/vendor-LICENSES.md`（随 skill 分发的登记件）。

## 一、捆绑的 JS 库（内嵌于审阅页单文件 HTML）

三个库均为 **MIT** 许可，与套件主 LICENSE 兼容。`build_review_page.py` 将其全文内嵌进单文件审阅页——
许可头随页面分发旅行，满足 MIT 对副本携带版权与许可声明的要求。
dagre 与 cytoscape-dagre 的上游 dist/构建不带许可头，2026-11-11 已在 vendored 文件头部补注 MIT 全文
（原始代码字节未改动；补注登记与 sha256 见 vendor-LICENSES.md）。

### 1. cytoscape.js 3.30.4

- 上游：https://github.com/cytoscape/cytoscape.js
- 用途：审阅页类图渲染（单文件 HTML 内嵌）

```text
Copyright (c) 2016-2024, The Cytoscape Consortium.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the “Software”), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 2. dagre 0.8.5

- 上游：https://github.com/dagrejs/dagre
- 用途：审阅页类图有向层次布局（cytoscape-dagre 的布局引擎）
- 版本核验：与上游 v0.8.5 `dist/dagre.min.js` 字节级哈希一致（2026-11-11）

```text
Copyright (c) 2012-2014 Chris Pettitt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

### 3. cytoscape-dagre（版本未确证，sha256 锁定）

- 上游：https://github.com/cytoscape/cytoscape.js-dagre
- 用途：cytoscape.js 的 dagre 布局扩展
- 版本注记：与上游 npm dist 2.0.0-2.3.2 哈希均不一致（疑为仓库 master 构建），按 sha256 锁定；
  许可文本取自上游项目 LICENSE（对该项目各版本一致适用）

```text
Copyright (c) 2016-2018, 2020, The Cytoscape Consortium.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the “Software”), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 二、运行依赖（pip 单独安装，不随套件捆绑）

| 依赖 | 实证版本 | 许可 | 核验来源 |
|---|---|---|---|
| rdflib | 7.6.0 | BSD-3-Clause | pip 包元数据 License 字段 |
| owlready2 | 0.51 | LGPL-3.0 | 安装包 dist-info `LICENSE.txt`（GNU Lesser General Public License v3） |
| pyshacl | 0.29.1 | Apache-2.0 | pip 包元数据 License 字段 + Classifier（Apache Software License） |

**pyshacl 传递依赖**（R4 SHACL 约束校验层，pip 自动解析安装，不随套件捆绑）：

| 依赖 | 实证版本 | 许可 | 核验来源 |
|---|---|---|---|
| owlrl | 7.6.2 | W3C-20150513 | 安装包 dist-info `LICENSE.txt`（W3C Software and Document Notice and License） |
| html5rdf | 1.2.1 | MIT | 安装包 dist-info `LICENSE`（rdflib[html] 传递） |
| prettytable | 3.16.0 | BSD-3-Clause | 安装包 dist-info `licenses/LICENSE` |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | 安装包 dist-info `LICENSE`（双许可任选其一） |
| importlib-metadata | 8.7.1 | Apache-2.0 | 安装包 dist-info `LICENSE`（仅 Python <3.12 需要） |

- 上述依赖经 `requirements.txt` 由 pip 安装（pyshacl 传递依赖自动解析），**不捆绑进套件发行包**；各自按其许可条款分发。
- 套件代码以 import 方式调用、不修改不静态链接——LGPL-3.0（owlready2）依赖与套件 MIT 许可兼容；pyshacl 全链 Apache-2.0/BSD/MIT/W3C 无 copyleft 传染。
- **owlrl W3C-20150513 NOTICE 注记**：W3C 软件许可要求再分发时保留原始版权与许可声明。pip 单独安装不捆绑→套件发行包不含 owlrl 字节，NOTICE 义务随 pip 包自身分发承接；若未来捆绑 owlrl 须随附其 `LICENSE.txt` 全文。
- owlready2 内置 Pellet/HermiT 推理机 jar（L3 通道），其许可随 owlready2 包分发；
  引擎行为限制登记见 `skills/ontology-model/references/reasoner-limits.md`。
- pyshacl 为 R4 SHACL 层核心依赖（纯 Python 无 Java，与 Java 推理机两条正交环境轴）；validate_shacl 显式 `advanced=True`/`inference=None`，不启用 owlrl 推理闭包（owlrl 仅作 pyshacl 内部依赖安装，MVP 坚持输入侧断言数据口径）。
- Java 运行时与 node 为用户环境组件，不随套件分发。

## 三、方法论来源致谢（非许可依赖）

本体建模方法论内核（`skills/ontology-model/references/methodology-core.md`）源自
《本体驱动的AI数据管理》（编写组著）一书的公开方法论，经知识卡片蒸馏后按管线 Stage 重编译为
自包含执行判据（逐条括注来源卡 ID）。套件不复制原书文本；方法论思想的使用在此致谢。
