# storage-abstraction — Discovery Brief

## 问题描述
文件存储是 BidSmart 的基础设施。需要支持本地文件系统存储，同时预留加密存储和未来云存储（OSS/S3）的扩展点。通过抽象层实现存储后端可替换。

## 当前状态
- `src/storage/base.py`: StorageBackend 抽象类
- `src/storage/local.py`: LocalFileStorage 本地实现
- 路径规则: `{storage_root}/{project_id}/{uuid}.ext`
- `src/security/encryption.py`: EncryptedStorageBackend（可选加密包装）

## 边界
**In scope:** 本地磁盘存储、存储抽象接口、路径命名规则
**Out of scope:** 云存储接入（P2）、分布式文件系统、CDN
