# documents-pipeline — Discovery Brief

## 问题描述
BidSmart 需要接收用户上传的招标文件和投标文件，将文件安全存储并关联到项目。不同文件格式（.docx, .pdf, .txt）需要统一解析为可审查文本。

## 当前状态
- 后端 `src/platform/documents/` 提供上传/下载/列表 API
- 文件存储在 `storage/{project_id}/{uuid}.ext`
- 上传时自动校验文件大小（MAX_UPLOAD_SIZE_MB）
- 支持多文件并行上传
- 前端提供拖拽上传和点击上传两种方式

## 边界
**In scope:**
- 文件上传/下载/删除
- 多格式解析委托给 parsing 模块
- 文件归属项目
- 文件大小校验

**Out of scope:**
- 文件预览（P2）
- 分块上传（当前阶段）
- 文件版本管理
