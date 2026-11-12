# vendor 第三方库许可与版本锁定登记（N2）

> 本文件随 ontology-review skill 分发（权威侧 `.claude/skills/ontology-review/assets/`，套件快照同构）。
> 三个 JS 库经 `build_review_page.py` 的 `VENDORS` 注入内嵌进单文件审阅页 HTML——**许可头随页面分发旅行**，
> 满足 MIT「copyright notice + permission notice 须包含在所有副本或实质部分中」的要求。
> 套件根 `THIRD-PARTY-LICENSES.md` 为发行汇总件（含 pip 依赖许可注记），与本文件互为参照。

## 版本锁定登记表

| 库 | 版本 | 上游 | 许可 | 版权行 | 本地文件 sha256 |
|---|---|---|---|---|---|
| cytoscape.js | **3.30.4**（文件内 `version="3.30.4"` 字符串提取） | https://github.com/cytoscape/cytoscape.js | MIT | Copyright (c) 2016-2024, The Cytoscape Consortium | `1bb5340e549511e111b31e5684872c949ad33d40ea5dba0ad8e7d90c62c7b3b9` |
| dagre | **0.8.5**（与上游 v0.8.5 `dist/dagre.min.js` **字节级哈希一致**，2026-11-11 核验） | https://github.com/dagrejs/dagre | MIT | Copyright (c) 2012-2014 Chris Pettitt | `01ee29fcf782a4389225fe2b4ae8d19cd741a523857bd5a50457efbe1dabe7be`（含补注许可头；上游原始 dist sha256=`62eb9787ccfdbdf4148d4d99d31dbf9ee4770eafee81e637d759b52aac22cd51`） |
| cytoscape-dagre | **未确证**——与上游 npm dist 2.0.0/2.1.0/2.2.0/2.3.0/2.3.1/2.3.2 哈希均不一致，疑为仓库 master 构建；**按 sha256 锁定**，升级时须重新核验上游 | https://github.com/cytoscape/cytoscape.js-dagre | MIT | Copyright (c) 2016-2018, 2020, The Cytoscape Consortium | `0e36d28ea42c29b08b51af8965382583a6da8ebac53b4edb9de25785fac57f16`（含补注许可头；补注前本地 sha256=`bf70fe402991dcbff33e05a7e4a5271c78020bb75e85d1c80ab7538e4157112e`） |

**许可兼容性**：三库均 MIT，与套件主 LICENSE（MIT）兼容，无 copyleft 传染。

## 补注登记（2026-11-11，Phase C N2）

- cytoscape.min.js 上游 dist 自带完整 MIT 许可头——**未改动**。
- dagre.min.js 与 cytoscape-dagre.js 上游 dist/构建**不带许可头**——本次在文件头部补注 MIT 许可全文注释块（版权行+许可文本逐字取自上游 LICENSE，经 jsdelivr npm 包渠道获取）。**原始代码字节未改动**，仅前置注释。
- 补注后验证：`node --check` 两文件语法通过；`self_test.py` 全链 10/10 PASS（E7 页面构建无占位符残留 + E9 内嵌 JS 语法）。
- 核验方法：curl 上游 dist 到隔离临时目录做 sha256 比对（**只比对不运行**），用后即清。

## 许可全文

### cytoscape.js 3.30.4（ vendored 文件自带许可头，逐字如下）

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

### dagre 0.8.5（上游 LICENSE 逐字，jsdelivr npm 包渠道获取）

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

### cytoscape-dagre（上游 LICENSE 逐字，jsdelivr npm 包渠道获取）

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
