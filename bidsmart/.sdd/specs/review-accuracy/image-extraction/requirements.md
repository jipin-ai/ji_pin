# Requirements: 图片提取与识别

## 概述

在文档解析阶段提取 DOCX/PDF 中的嵌入图片，通过 DeepSeek Vision API 转为文字，注入解析流。

## EARS 需求

### R1: DOCX 图片提取

**WHEN** 解析 .docx 文件  
**THEN** 通过 zipfile 提取 `word/media/` 下的所有图片文件  
**WHERE** 每张图片记录文件名、归属章节、页码

### R2: PDF 图片提取

**WHEN** 解析 .pdf 文件  
**THEN** 通过 pymupdf `page.get_images()` 提取每页嵌入图片  
**WHERE** 图片与所在页码绑定

### R3: DeepSeek Vision 识别

**WHEN** 图片提取完成后  
**THEN** 将图片 base64 编码，调用 DeepSeek Vision API 识别文字内容  
**WHERE** 返回结构化文字（表格→Markdown表格，公章→"公章内容：XXX"，普通图→描述文本）

### R4: 图片文字注入解析流

**WHEN** DeepSeek Vision 返回识别结果后  
**THEN** 将文字内容注入到对应章节的 `section.content` 末尾  
**WHERE** 标注 `[图片识别]` 前缀以区分原文与识别内容

### R5: .emf 格式支持

**WHEN** 遇到 .emf 格式图片  
**THEN** 使用 Pillow 将 .emf 转为 PNG 后再送 DeepSeek Vision  
**WHERE** 转换失败时记录警告并跳过

### R6: 并发控制

**WHEN** 文档包含超过 50 张图片  
**THEN** 分批并发处理，每批最多 5 张图  
**WHERE** 避免 API rate limit

### R7: 性能约束

**WHEN** 处理 294 张图片的文档  
**THEN** 图片识别总耗时不超过 120 秒  
**WHERE** 超时图片标记为 "识别超时" 并继续

### R8: 向后兼容

**WHEN** 图片提取功能上线后  
**THEN** `POST /ai/review-file` 和 `POST /ai/review-file/stream` 响应格式不变  
**WHERE** 图片识别文字作为 section.content 的一部分自然融入
