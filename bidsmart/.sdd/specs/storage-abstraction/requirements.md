# storage-abstraction — 需求规格 (EARS)

## 功能需求

### FR-1: 抽象存储接口 (Ubiquitous)
**While** 任何模块需要文件存储，**the system shall** 使用 `StorageBackend` 抽象接口（save/get/delete），不直接依赖具体实现。

**验收标准:**
- [x] `async save(project_id, content, extension) → str` — 返回存储路径
- [x] `async get(path) → bytes` — 读取文件内容
- [x] `async delete(path) → None` — 删除文件

### FR-2: 本地文件系统存储 (State-driven)
**Where** 部署在单机环境，**the system shall** 使用 `LocalFileStorage` 实现，文件存储在 `{root}/{project_id}/{uuid}.ext`。

**验收标准:**
- [x] 自动创建项目目录
- [x] UUID 文件名保证唯一性
- [x] 存储根目录可配置（STORAGE_ROOT）

### FR-3: 透明加密包装 (Optional, State-driven)
**Where** 需要静态加密，**the system shall** 支持 `EncryptedStorageBackend` 包装任意 StorageBackend，透明加密/解密。

**验收标准:**
- [x] 加密格式: [1B ver][12B nonce][ct+tag]
- [x] 调用方无需感知加密
- [x] 解密失败返回明确错误
