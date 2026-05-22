# image-extraction: 文档图片提取与识别

## 问题

当前 PDF/DOCX 解析器（`pdf_parser.py` / `docx_parser.py`）只提取文字，文档中嵌入的图片被静默丢弃。实测：
- 投标文件.docx 含 **294 张图片**（PNG/JPEG）
- 技术暗标.docx 含 **11 张 .emf 矢量图**
- 全部丢失，LLM 未见到投标文件 60%+ 的核心内容

这是与「匹配盲猜」并列的第二大致命精准度问题。

## 方案

**DeepSeek Vision API 图片识别**

```
pymupdf/zipfile 提取图片
  → base64 编码
  → DeepSeek Vision API (deepseek-chat 多模态)
  → 返回图片文字描述/内容识别
  → 插入解析流（归属到对应章节）
```

### 为什么选 DeepSeek Vision 而非本地 OCR
- ECS 只有 4G RAM，PaddleOCR 需要 ~2GB
- DeepSeek Vision 不只是 OCR——能理解公章、表格、资质证书的语义
- 已有 API key 和 AsyncOpenAI 客户端，零额外依赖

## 范围

- DOCX：通过 zipfile 提取 `word/media/` 下的图片
- PDF：通过 pymupdf `page.get_images()` 提取嵌入图片
- 图片送 DeepSeek Vision 识别，返回文字注入到对应章节
- 支持 .png/.jpg/.jpeg/.emf（.emf 需转 PNG）

## 不包含

- 独立图片文件上传（只处理文档内嵌图片）
- 图片存储/管理/预览系统
- 图片相似度/去重

## 依赖

- DeepSeek Vision API（deepseek-chat 已支持多模态）
- pymupdf（已安装）
- Pillow（.emf → PNG 转换，需新增）

## 预期效果

- 精准度从 50-60%（P0 语义匹配后）→ 75-85%（图片信息补全后）
