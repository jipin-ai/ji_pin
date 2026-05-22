# parsing-engine — 需求规格 (EARS)

## 功能需求

### FR-1: 多格式文档解析 (State-driven)
**Where** 系统接收上传文档，**the system shall** 根据文件扩展名自动选择解析器（.docx → DocxParser, .pdf → PdfParser, .txt → 直接读取）。

**验收标准:**
- [x] .docx: python-docx 提取段落文本，保留段落结构
- [x] .pdf: pymupdf 提取页面文本，标注页码
- [x] .txt: UTF-8 编码直接读取
- [x] 不支持的格式返回明确错误

### FR-2: 统一解析接口 (Ubiquitous)
**While** 任何模块调用文档解析，**the system shall** 使用统一的 `parse_document(path) → ParsedDocument` 接口。

**验收标准:**
- [x] ParsedDocument 含 text + pages + metadata
- [x] 解析器通过工厂函数注册和选择

### FR-3: 大文件处理 (Event-driven)
**When** 解析大文件（> 10MB），**the system shall** 流式读取避免内存溢出。

**验收标准:**
- [x] .docx 分段落读取
- [x] .pdf 分页读取
