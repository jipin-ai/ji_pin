# Design: 图片提取与识别

## 架构

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ pdf_parser   │────▶│ ImageExtractor  │────▶│ DeepSeek Vision  │
│ docx_parser  │     │ (新增模块)       │     │ API              │
└──────────────┘     └────────┬────────┘     └────────┬─────────┘
                              │                        │
                              ▼                        ▼
                     ParsedDocument             识别文字注入
                     .sections[].content        section.content
```

## 新增模块

### `src/parsing/image_extractor.py`

```python
class ImageExtractor:
    """提取文档嵌入图片，送 DeepSeek Vision 识别"""

    async def extract_from_docx(path: str) -> list[ExtractedImage]:
        """从 DOCX 提取 word/media/ 下图片"""
    
    async def extract_from_pdf(path: str) -> list[ExtractedImage]:
        """从 PDF 提取嵌入图片（pymupdf）"""

    async def recognize_image(client, image: ExtractedImage) -> str:
        """单张图片送 DeepSeek Vision，返回文字"""

    async def recognize_batch(images: list[ExtractedImage], batch_size=5) -> list[str]:
        """分批并发识别"""

@dataclass
class ExtractedImage:
    data: bytes           # 原始图片数据
    format: str           # png/jpeg/emf
    page_number: int      # 所在页码
    section_heading: str  # 归属章节标题
    index: int            # 图片序号
```

### DeepSeek Vision 调用

```python
# deepseek-chat 支持多模态 image_url
response = await client.chat.completions.create(
    model="deepseek-chat",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "请识别这张图片中的文字内容。如果是表格，用Markdown表格格式输出。"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]
    }],
    max_tokens=1000,
)
```

### .emf 转换

```python
from PIL import Image
# .emf → PNG (Pillow 支持读取 .emf，需额外安装)
img = Image.open(io.BytesIO(emf_data))
buf = io.BytesIO()
img.save(buf, format="PNG")
png_data = buf.getvalue()
```

## 文件变更清单

1. **`src/parsing/image_extractor.py`** — 新文件，核心逻辑
2. **`src/parsing/pdf_parser.py`** — `parse()` 结尾调用 `ImageExtractor.extract_from_pdf()`
3. **`src/parsing/docx_parser.py`** — `parse()` 结尾调用 `ImageExtractor.extract_from_docx()`
4. **`pyproject.toml`** — 新增 `Pillow>=10.0`, 版本 0.8.1→0.8.2
5. **`src/config.py`** — 新增 `image_recognition_batch_size: int = 5`, `image_recognition_timeout: int = 120`
6. **`src/main.py`** — 版本 0.8.2

## 不改变

- API 端点签名和响应格式
- ParsedDocument / Section 数据模型
- 前端 index.html
- review pipeline 逻辑
