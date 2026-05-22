# projects-crud — 需求规格 (EARS)

## 功能需求

### FR-1: 创建项目 (Event-driven)
**When** 用户创建新项目，**the system shall** 校验必填字段（项目名称）→ 写入数据库 → 返回完整项目对象。

**验收标准:**
- [x] 必填：name；选填：department, editor, bid_time
- [x] 创建成功后自动设为当前项目
- [x] 名称非空校验

### FR-2: 项目列表 (State-driven)
**Where** 首页项目列表，**the system shall** 分页展示所有项目（名称、部门、文件数、创建时间）。

**验收标准:**
- [x] 分页支持（page + page_size）
- [x] 按创建时间倒序
- [x] admin 看全部，其他角色只看有权限的项目

### FR-3: 项目详情 (State-driven)
**Where** 点击项目，**the system shall** 展示项目详情（全部元数据 + 文件列表）。

**验收标准:**
- [x] `GET /projects/{id}` 返回完整信息
- [x] 含文件数量和最近活动时间

### FR-4: 更新/删除项目 (Event-driven)
**When** 项目所有者/管理员修改或删除项目，**the system shall** 更新字段或删除项目（级联删除关联文件）。

**验收标准:**
- [x] PUT /projects/{id} 更新字段
- [x] DELETE /projects/{id} 级联删除文件
- [x] 权限校验
