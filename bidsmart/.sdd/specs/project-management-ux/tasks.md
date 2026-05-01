# project-management-ux — 实现任务

## 1. 项目创建表单
_Status: completed_
_Boundary: static/index.html `#projectCreateForm` 区域_
_Depends: none_

**Goal**: 在项目管理面板中添加创建项目表单。

**Acceptance Criteria:**
- [x] DB 已有 department/editor/bid_time 字段（前置完成）
- [x] API POST /projects 已支持新字段（前置完成）
- [x] 表单包含 4 个字段，项目名称必填
- [x] 提交成功后刷新项目列表并自动选中新项目

### 1.1 添加创建项目 HTML 表单 (P)
_Status: completed_
_已完成: projectCreateForm div (line 323-336)，包含 name/department/editor/bid_time 字段_

### 1.2 实现 createProjectFrontend() JS 函数
_Status: completed_
_已完成: createProject() 函数 (line 613-629)，调用 POST /projects，成功后调用 loadProjects() 刷新_

---

## 2. 项目列表展示
_Status: completed_
_Boundary: static/index.html `#projectList` 区域_
_Depends: 1_

**Acceptance Criteria:**
- [x] 项目以卡片展示：名称、部门、文件数、时间
- [x] 点击选中，高亮显示，设置 currentProjectId
- [x] 空列表时展示引导文案

### 2.1 重构项目列表渲染
_Status: completed_
_已完成: loadProjects() (line 536-560) 用 .project-card 卡片替代 <select> 下拉，含 proj-meta 显示部门/编辑人_

### 2.2 项目上下文全局状态
_Status: completed_
_已完成: currentProjectId (line 474) + selectProject(id) (line 566) + updateProjectContexts() (line 578-604)，选中项目自动切换到上传面板_

---

## 3. 文件上传面板 — 项目上下文
_Status: completed_
_Boundary: static/index.html `#uploadPanel` 区域_
_Depends: 2_

**Acceptance Criteria:**
- [x] 进入面板时若 currentProjectId 已设，显示项目名
- [x] 未设时提示先选项目
- [x] 上传完成后显示"前往文件审查"按钮

### 3.1 上传面板上下文绑定
_Status: completed_
_已完成: uploadFile() (line 654-689) 检查 currentProjectId，使用 updateProjectContexts() 显示项目名_

### 3.2 上传后操作引导
_Status: completed_
_已完成: uploadWorkflowLink (line 361) + 上传成功 .classList.add("show") (line 682)_

---

## 4. 文件审查面板 — 项目文件加载
_Status: pending_
_Boundary: static/index.html `#fileReviewPanel` 区域_
_Depends: 3_

**Acceptance Criteria:**
- [x] API GET /projects/{id}/documents 已实现（前置完成）
- [x] 文件清单以 checkboxes 列出（支持多选）
- [x] 两个文件都选中后启用审查按钮
- [ ] 审查结果正常展示（需端到端验证）

### 4.1 重构文件审查文件加载
_Status: completed_
_已完成: loadDocsForReview() (line 746-790) 使用 GET /projects/{id}/documents，checkboxes 替代下拉框_

### 4.2 审查流程串联验证
_Status: pending_
_需执行: 创建项目 → 上传招标+投标文件 → 文件审查 → 结果展示_

---

## 5. 优化收尾
_Status: pending_
_Boundary: static/index.html_
_Depends: 4_

**Acceptance Criteria:**
- [x] "手动输入" 已改为可折叠区域（uploadPanel 内）
- [ ] 文件审查完成后，项目卡片更新审查状态
- [x] 全局 4-Tab 结构：📁项目管理 | 📄文件上传 | 📊文件审查 | 📋对照表

### 5.1 UI 清理
_Status: completed_
_已完成: 手动输入改为可折叠 toggleManualInput() (line 697)，4 Tab 无多余的"手动输入"Tab_

### 5.2 端到端验证
_Status: pending_
_需执行: 用实际招标/投标文件走完整流程确认无断裂_
