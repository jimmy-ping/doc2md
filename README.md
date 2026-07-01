# doc2md — 文档转 Markdown 工具

支持 PDF / Word (.docx) / PowerPoint (.pptx) / Excel (.xlsx) / TXT → Markdown，自动提取图片。

## 安装

```bash
pip install pymupdf python-docx python-pptx openpyxl Pillow
# 可选：brew install pandoc（用于 DOCX/PPTX 回退转换）
```

## 用法

### CLI

```bash
# 转换单个文件
python3 doc2md.py convert report.pdf

# 指定输出目录
python3 doc2md.py convert report.docx -o output/

# 批量转换
python3 doc2md.py batch docs/ *.pdf -o output/

# 对 DOCX/PPTX 使用 Pandoc
python3 doc2md.py convert slides.pptx --pandoc
```

### GUI

```bash
python3 doc2md.py gui
```

或双击 `doc2md.command`。

### 输出结构

```
report_md/
├── report.md          # Markdown 文件
└── images/
    ├── img_001.png    # 提取的图片
    └── img_002.png
```

## 支持的格式

| 格式 | 扩展名 | 引擎 | 图片提取 |
|---|---|---|---|
| PDF | .pdf | PyMuPDF | ✅ |
| Word | .docx, .doc | python-docx | ✅ |
| PowerPoint | .pptx, .ppt | python-pptx | ✅ |
| Excel | .xlsx, .xls | openpyxl | ✅ |
| 纯文本 | .txt, .md, .csv | 标准库 | — |
| 通用回退 | .docx, .pptx 等 | Pandoc | ✅ |

## 运行测试

```bash
pytest tests/ -v
```
