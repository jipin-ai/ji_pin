# parsing-engine — Discovery Brief

## 问题描述
标书审查需要从多种格式的文档中提取文本内容。招标文件和投标文件通常为 .docx（Word）或 .pdf 格式。需要统一的解析接口支持多格式，并提供扩展点。

## 当前状态
- `src/parsing/base.py`: 抽象解析器接口
- `src/parsing/docx_parser.py`: python-docx 解析 Word 文档
- `src/parsing/pdf_parser.py`: pymupdf/fitz 解析 PDF 文档
- `src/parsing/models.py`: 解析结果数据模型

## 边界
**In scope:** .docx, .pdf, .txt 文本提取、段落/章节识别
**Out of scope:** 图片/表格 OCR、格式保留、扫描件处理
