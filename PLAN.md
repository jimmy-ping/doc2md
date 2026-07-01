# doc2md — 设计文档

## 概述
PDF/Word/PPT/Excel/TXT → Markdown 转换工具，自动提取图片，CLI+GUI 双入口。

## 技术选型
| 格式 | 解析库 |
|---|---|
| PDF | PyMuPDF (fitz) |
| DOCX | python-docx |
| PPTX | python-pptx |
| XLSX | openpyxl |
| TXT | 标准库 + chardet |
| 通用回退 | Pandoc |

## 架构
单文件双入口 (argparse `gui` 子命令 → tkinter)，转换器分层：
- `converters/base.py` — ConversionResult + BaseConverter ABC
- `converters/{fmt}_converter.py` — 各格式独立转换器
- `utils.py` — 路径/文件名/写入工具函数
- `doc2md.py` — CLI + GUI 入口，`convert_file()` 为共享核心

## 设计决策
1. 不全部用 Pandoc（无法提取 PDF/PPTX 图片，无进度反馈）
2. 图片统一转 PNG，顺序命名 `img_001.png`
3. DOCX 用 XML 元素遍历保证段落/表格/图片顺序
4. PDF 图片位置根据 rect 近似判断（页首/页尾）
