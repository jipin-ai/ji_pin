# documents-pipeline — 需求规格 (EARS)

## 功能需求

### FR-1: 文件上传 (Event-driven)
**When** 用户在项目下上传文件，**the system shall** 接收文件 → 校验大小（不超过 MAX_UPLOAD_SIZE_MB）→ 生成 UUID 文件名 → 保存到 `storage/{project_id}/{uuid}.ext` → 返回文件元数据。

**验收标准:**
- [x] 支持拖拽上传和点击上传
- [x] 文件大小超限返回 413 错误
- [x] 文件名唯一（UUID + 原始扩展名）
- [x] 上传成功后文件列表即时刷新

### FR-2: 文件下载 (Event-driven)
**When** 用户请求下载文件，**the system shall** 返回文件流（`StreamingResponse`），文件名使用原始上传名称。

**验收标准:**
- [x] Content-Disposition 包含原始文件名
- [x] 文件不存在返回 404

### FR-3: 项目文件列表 (State-driven)
**Where** 用户查看项目文件，**the system shall** 列出该项目下所有文件（名称、大小、上传时间、类型）。

**验收标准:**
- [x] `GET /projects/{project_id}/documents` 返回文件列表
- [x] 空项目返回空数组
- [x] 按上传时间倒序

### FR-4: 文件删除 (Event-driven)
**When** 项目所有者/管理员删除文件，**the system shall** 删除文件记录和物理文件 → 返回成功确认。

**验收标准:**
- [x] 物理文件从 storage/ 中删除
- [x] 数据库记录删除
- [x] 无权限用户返回 403

### FR-5: 文件类型识别 (Ubiquitous)
**While** 文件上传，**the system shall** 根据扩展名识别文件类型（tender=招标文件 / bid=投标文件 / attachment=附件）。

**验收标准:**
- [x] 前端可选文件类型标签
- [x] API schema 包含 doc_type 字段
