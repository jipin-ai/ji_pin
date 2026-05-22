# projects-crud — Discovery Brief

## 问题描述
投标项目是 BidSmart 的核心组织单元。每个投标项目包含项目元信息（名称、部门、编辑人、投标时间），以及关联的招标文件和投标文件。需要完整的 CRUD 操作来管理项目生命周期。

## 当前状态
- 后端 `src/platform/projects/` 提供完整 REST API
- Project 模型含 department/editor/bid_time 扩展字段（v0.4.0 migration）
- 前端以项目卡片形式展示，替代早期下拉框
- 项目创建后自动跳转文件上传面板

## 边界
**In scope:** 项目 CRUD、元数据管理、项目列表分页、RBAC 过滤
**Out of scope:** 项目成员管理（ProjectMember 模型已有，P2 接入）、项目模板
