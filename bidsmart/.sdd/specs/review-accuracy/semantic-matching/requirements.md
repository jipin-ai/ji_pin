# Requirements: 语义匹配

## 概述

用 BGE 语义向量相似度替代 `_keyword_overlap()` 纯关键词重叠匹配，消除 blind-fallback 随机映射。

## EARS 需求

### R1: 语义匹配

**WHEN** `match_sections()` 为每条招标条款寻找最匹配的投标段落  
**THEN** 使用 BGE embedding 计算招标条款与投标段落间的余弦相似度  
**WHERE** 相似度最高的段落被选为匹配结果

### R2: 回退保留（降级兼容）

**WHEN** 语义匹配得分低于阈值（默认 0.2）  
**THEN** 保留当前位置比例 fallback 作为兜底  
**WHERE** fallback 的 `confidence` 标记为 0.01 以示区分

### R3: 匹配置信度透传

**WHEN** 匹配完成后  
**THEN** 每条 `MatchedSection.confidence` 反映真实的 embedding 相似度（0-1）  
**WHERE** 前端可显示匹配可信度供用户参考

### R4: 性能约束

**WHEN** 处理大型招标文件（>100 条条款）  
**THEN** 匹配阶段耗时不超过 5 秒  
**WHERE** 使用批量 embedding（一次 encode 所有段落）

### R5: 依赖声明

**WHEN** 部署时  
**THEN** `pyproject.toml` 必须声明 `sentence-transformers` 依赖  
**WHERE** `pip install` 后可直接运行

### R6: 向后兼容

**WHEN** 新匹配逻辑上线后  
**THEN** `POST /ai/review-file` 和 `POST /ai/review-file/stream` 的响应格式不变  
**WHERE** `match_count`、`match_confidence` 字段继续保持
