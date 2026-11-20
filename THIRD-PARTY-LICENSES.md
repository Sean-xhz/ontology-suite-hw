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
| pypdf | 6.14.2 | BSD-3-Clause | pip 包元数据 License-Expression 字段（ingest 2.0 PDF 文本层 inventory） |
| pypdfium2 | 5.11.0 | BSD-3-Clause OR Apache-2.0 | pip 包元数据 License 字段「BSD-3-Clause, Apache-2.0」（双许可任选；wheel 自带 pdfium 二进制 BSD-3-Clause；ingest 2.0 PDF→页图渲染） |
| python-docx | 1.2.0 | MIT | pip 包元数据 License-Expression 字段（ingest 2.0 Word substrate/inventory） |
| openpyxl | 3.1.5 | MIT | pip 包元数据 License-Expression 字段（ingest 2.0 Excel substrate/inventory） |
| python-pptx | 1.0.2 | MIT | pip 包元数据 License-Expression 字段（ingest 2.0 PPT 位置 substrate/inventory） |
| Pillow | 11.3.0 | MIT-CMU | pip 包元数据 License-Expression 字段（ingest 2.0 图片元数据/解码/PNG 编码） |

**pyshacl 传递依赖**（R4 SHACL 约束校验层，pip 自动解析安装，不随套件捆绑）：

| 依赖 | 实证版本 | 许可 | 核验来源 |
|---|---|---|---|
| owlrl | 7.6.2 | W3C-20150513 | 安装包 dist-info `LICENSE.txt`（W3C Software and Document Notice and License） |
| html5rdf | 1.2.1 | MIT | 安装包 dist-info `LICENSE`（rdflib[html] 传递） |
| prettytable | 3.16.0 | BSD-3-Clause | 安装包 dist-info `licenses/LICENSE` |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | 安装包 dist-info `LICENSE`（双许可任选其一） |
| importlib-metadata | 8.7.1 | Apache-2.0 | 安装包 dist-info `LICENSE`（仅 Python <3.12 需要） |

**ingest 2.0 解析渲染六库传递依赖**（ontology-ingest I1，pip 自动解析安装，不随套件捆绑）：

| 依赖 | 实证版本 | 许可 | 核验来源 |
|---|---|---|---|
| lxml | 6.1.3 | BSD-3-Clause | pip 包元数据 License-Expression 字段（python-docx/python-pptx 传递） |
| et-xmlfile | 2.0.0 | MIT | pip 包元数据 License-Expression 字段（openpyxl 传递） |
| typing_extensions | 4.16.0 | PSF-2.0 | pip 包元数据 License-Expression 字段（pypdf 在 Python <3.11 必需，CI 3.9 矩阵会装） |
| XlsxWriter | 3.2.9 | BSD-2-Clause | pip 包元数据 License-Expression 字段（python-pptx 硬传递） |

- 上述依赖经 `requirements.txt` 由 pip 安装（pyshacl 传递依赖自动解析），**不捆绑进套件发行包**；各自按其许可条款分发。
- 套件代码以 import 方式调用、不修改不静态链接——LGPL-3.0（owlready2）依赖与套件 MIT 许可兼容；pyshacl 全链 Apache-2.0/BSD/MIT/W3C 无 copyleft 传染。
- **owlrl W3C-20150513 NOTICE 注记**：W3C 软件许可要求再分发时保留原始版权与许可声明。pip 单独安装不捆绑→套件发行包不含 owlrl 字节，NOTICE 义务随 pip 包自身分发承接；若未来捆绑 owlrl 须随附其 `LICENSE.txt` 全文。
- owlready2 内置 Pellet/HermiT 推理机 jar（L3 通道），其许可随 owlready2 包分发；
  引擎行为限制登记见 `skills/ontology-model/references/reasoner-limits.md`。
- pyshacl 为 R4 SHACL 层核心依赖（纯 Python 无 Java，与 Java 推理机两条正交环境轴）；validate_shacl 显式 `advanced=True`/`inference=None`，不启用 owlrl 推理闭包（owlrl 仅作 pyshacl 内部依赖安装，MVP 坚持输入侧断言数据口径）。
- **ingest 2.0 解析渲染六库全链无 copyleft**：pypdf BSD-3 / pypdfium2 BSD-3 OR Apache-2.0 / python-docx MIT / openpyxl MIT / python-pptx MIT / Pillow MIT-CMU，传递依赖 lxml BSD-3 / et-xmlfile MIT / typing_extensions PSF-2.0 / XlsxWriter BSD-2——均与套件 MIT 许可兼容，经 import 调用、不修改不捆绑。输出字节稳定性版本敏感（精确钉住，升级须重跑双跑确定性）。pypdfium2 wheel 自带 pdfium 二进制（BSD-3-Clause，Chromium pdfium），随 pip 包分发不另行捆绑。
- **PyMuPDF（fitz）零代码路径——不引入**：PyMuPDF 采用 **AGPL-3.0 或 Artifex 商业双许可**，AGPL copyleft 强于 LGPL，import 即运行时链接 copyleft 代码，MIT 套件分发该路径有污染争议（Artifex 立场从严）。套件**连可选 import 都不写**——PDF 渲染用 **pypdfium2**（BSD-3/Apache-2.0，MIT 兼容）替代 fitz 栅格化，文本层 inventory 用 pypdf（BSD-3）。poppler（pdf2image 后端）/ tesseract（OCR）/ 本地 VLM（MinerU AGPL / Marker GPL）为系统二进制或 copyleft/重依赖，违通用性 + 许可不兼容，同样不引入。详见 `skills/ontology-ingest/references/parsing-limits.md` ⑧⑨。
- **LibreOffice（可选系统前置，MPL-2.0）**：office（pptx/docx/xlsx）→PDF 全视觉渲染增强经 `soffice --headless --convert-to pdf` **独立子进程**调用，不 import 不静态链接——MPL-2.0 是文件级 copyleft（仅约束被修改的 MPL 源文件本身），不感染经子进程调用的 MIT 套件代码。用户按需 `brew install --cask libreoffice`（~700MB），不随套件分发；无则 office 退 substrate-only（纯 pip 主路径仍工作）。详见 parsing-limits.md ⑩。
- **pypdf[crypto] 可选 extra 默认未装**：RC4 加密 PDF 纯 Python 可解；AES 加密需 cryptography（pypdf[crypto]），未装时 `DependencyError`→exit2+提示 `pip install pypdf[crypto]`，不崩溃。cryptography 非套件默认依赖（用户按需自装）。
- Java 运行时与 node 为用户环境组件，不随套件分发。

## 三、方法论来源致谢（非许可依赖）

本体建模方法论内核（`skills/ontology-model/references/methodology-core.md`）源自
《本体驱动的AI数据管理》（编写组著）一书的公开方法论，经知识卡片蒸馏后按管线 Stage 重编译为
自包含执行判据（逐条括注来源卡 ID）。套件不复制原书文本；方法论思想的使用在此致谢。
