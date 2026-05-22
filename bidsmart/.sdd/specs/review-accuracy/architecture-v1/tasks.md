# Tasks: architecture-v1

## 版本
v0.9.0 → v1.0.0 (架构级重构)

## 新增模块 (5个)

### M1: structured_matcher.py
- [ ] 提取编号层级树 (3.1 → 3.1.1 → 3.1.2)
- [ ] 结构化对齐: 招标条款编号 → 投标章节编号映射
- [ ] 输出 alignment_score

### M2: multi_matcher.py  
- [ ] Path A: 结构化对齐得分
- [ ] Path B: BGE embedding cosine sim
- [ ] Path C: BM25 关键词得分
- [ ] 三路加权融合 → agreement_score

### M3: dual_verifier.py
- [ ] Path A: LLM 验证"段落是否回应要求"
- [ ] Path B: LLM 验证"要求应在哪个位置回应"
- [ ] Cross-check: 两路径指向同一段落 → 通过

### M4: excerpt_extractor.py
- [ ] LLM 从匹配段落摘录相关原文 (≤500字)
- [ ] 输出 relevant_excerpt

### M5: cross_validator.py
- [ ] red 级条款: 同一输入→两次独立审查
- [ ] 对比判定: 一致→确认, 不一致→unable_to_judge

## 重构

### pipeline.py → 6-stage pipeline
- [ ] Stage 0: 结构化解析 → structured_matcher
- [ ] Stage 1: 多策略匹配 → multi_matcher  
- [ ] Stage 2: 双路径反思 → dual_verifier
- [ ] Stage 3: 精确定位 → excerpt_extractor
- [ ] Stage 4: 合规审查 (带法规上下文)
- [ ] Stage 5: 交叉验证 (red级) → cross_validator
- [ ] Stage 6: 聚合+风险评分

## 回滚 v0.9 临时补丁
- [ ] 移除 match_low_confidence / match_medium_confidence 配置
- [ ] 移除软验证逻辑 (notes 方案)
- [ ] 移除 verify_match 硬门改软门
- [ ] 保留: 新 prompt、review_memory、image_extraction

## 验证
- [ ] 版本 1.0.0 (pyproject + main.py)
- [ ] uvicorn 无 import 错误
- [ ] health check 通过
- [ ] 前端 JS 语法
