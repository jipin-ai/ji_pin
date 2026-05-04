# Tasks: 图片提取与识别

## T1: 添加依赖
- [ ] `pyproject.toml`: dependencies 新增 `"Pillow>=10.0"`
- [ ] `pyproject.toml`: version → `0.8.2`

## T2: 配置扩展
- [ ] `src/config.py`: 新增 `image_recognition_batch_size: int = 5`
- [ ] `src/config.py`: 新增 `image_recognition_timeout: int = 120`
- [ ] `src/main.py`: version → `0.8.2`

## T3: 实现 ImageExtractor 模块
- [ ] 创建 `src/parsing/image_extractor.py`
- [ ] `ExtractedImage` dataclass
- [ ] `extract_from_docx(path)` — zipfile 提取 word/media/
- [ ] `extract_from_pdf(path)` — pymupdf get_images() + extract_image()
- [ ] `_convert_emf_to_png(data)` — Pillow .emf → PNG
- [ ] `recognize_image(client, image)` — DeepSeek Vision API 调用
- [ ] `recognize_batch(images, batch_size)` — asyncio.gather 分批并发

## T4: 注入解析器
- [ ] `src/parsing/pdf_parser.py`: `PdfParser.parse()` 结尾调用 ImageExtractor
- [ ] `src/parsing/docx_parser.py`: `DocxParser.parse()` 结尾调用 ImageExtractor
- [ ] 识别文字追加到 section.content 末尾，标注 `[图片识别]`

## T5: 版本号
- [ ] 确认 `pyproject.toml` 和 `src/main.py` 都显示 0.8.2

## T6: 重启 + 验证
- [ ] `fuser -k 39001/tcp; sleep 1`
- [ ] 启动 uvicorn 确认无 import 错误
- [ ] `curl -s http://localhost:39001/health` → `{"status":"ok","version":"0.8.2"}`
- [ ] 前端 JS 语法检查

## T7: 实测
- [ ] 上传投标文件.docx（294 张图）→ 查看 section.content 是否包含 `[图片识别]`
- [ ] 确认审查结果引用了图片识别内容
