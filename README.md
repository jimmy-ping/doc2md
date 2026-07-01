# doc2md — 文档转 Markdown 工具

将办公文档转换为 Markdown 格式，自动提取图片。支持 6 种格式，CLI + GUI 双入口。

## 快速开始

```bash
# 安装核心依赖
pip install pymupdf python-docx python-pptx openpyxl Pillow chardet

# 可选：Pandoc 回退引擎（用于无法用原生库解析的 DOCX/PPTX）
brew install pandoc
```

## 用法

### CLI

```bash
# 转换单个文件
python3 doc2md.py convert report.pdf

# 指定输出目录
python3 doc2md.py convert report.docx -o output/

# 批量转换
python3 doc2md.py batch docs/ -o output/

# 对 DOCX/PPTX 强制使用 Pandoc
python3 doc2md.py convert slides.pptx --pandoc
```

### GUI

```bash
python3 doc2md.py gui
```

或双击桌面的 `doc2md.command` 快捷方式。

## 支持格式

| 格式 | 扩展名 | 解析引擎 | 图片提取 | 说明 |
|------|--------|----------|----------|------|
| PDF | .pdf | PyMuPDF | ✅ | 含图片位置近似判断 |
| Word | .docx, .doc | python-docx | ✅ | XML 元素遍历保序 |
| PowerPoint | .pptx, .ppt | python-pptx | ✅ | 幻灯片逐页提取 |
| Excel | .xlsx, .xls | openpyxl | ✅ | 表格内容 + 内嵌图片 |
| 纯文本 | .txt, .md, .csv | 标准库 + chardet | — | 自动检测编码 |
| 通用回退 | .docx, .pptx 等 | Pandoc | ✅ | 原生库解析失败时使用 |

## 架构

```
doc2md.py              # CLI + GUI 入口，convert_file() 为共享核心
utils.py               # 路径处理、文件名安全化、Markdown 写入
converters/
├── base.py            # ConversionResult + BaseConverter ABC
├── pdf_converter.py   # PyMuPDF 解析
├── docx_converter.py  # python-docx 解析
├── pptx_converter.py  # python-pptx 解析
├── xlsx_converter.py  # openpyxl 解析
├── txt_converter.py   # 纯文本 + 编码检测
└── pandoc_fallback.py # Pandoc 通用回退
```

## 输出结构

```
report_md/
├── report.md          # Markdown 正文
└── images/
    ├── img_001.png    # 提取的图片（统一 PNG，按序编号）
    ├── img_002.png
    └── ...
```

## 设计决策

| 决策 | 原因 |
|------|------|
| 不全用 Pandoc | Pandoc 无法提取 PDF/PPTX 内嵌图片，且无逐页进度反馈 |
| 图片统一转 PNG | 保证兼容性，顺序命名便于 Markdown 引用 |
| DOCX 用 XML 元素遍历 | 保证段落/表格/图片的出现顺序与原文一致 |
| PDF 图片位置近似判断 | 根据 rect 坐标判断在页首还是页尾，就近插入 |
| 单个输出目录 | 一个输入文件 → 一个同名目录（_md 后缀），结构清晰 |

## 测试

```bash
pytest tests/ -v
```

覆盖各格式转换器的纯逻辑测试。

## 依赖

- **Python** ≥ 3.8
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF 解析
- [python-docx](https://python-docx.readthedocs.io/) — Word 解析
- [python-pptx](https://python-pptx.readthedocs.io/) — PowerPoint 解析
- [openpyxl](https://openpyxl.readthedocs.io/) — Excel 解析
- [Pillow](https://pillow.readthedocs.io/) — 图片处理
- [chardet](https://github.com/chardet/chardet) — 编码检测
- [Pandoc](https://pandoc.org/) — 可选，通用回退引擎

## 已知限制

- PDF 文本提取依赖 PyMuPDF 的 textpage，扫描版 PDF 需先用 OCR 工具预处理
- PPTX 中 SmartArt 图形和复杂动画内容无法提取
- Excel 合并单元格的 Markdown 表示为展开后的重复文本
- Pandoc 回退模式下图片提取能力取决于 Pandoc 版本
