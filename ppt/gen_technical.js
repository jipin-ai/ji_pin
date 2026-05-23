// 通睿 AI 安全网关 — 技术架构白皮书 PPT
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "通睿科技";
pres.title = "通睿 AI 安全网关 — 技术架构白皮书";

// ── Theme (Technical - more structured, monospace touches) ──
const C = {
  bg:      "0F172A",
  bgCard:  "1E293B",
  bgCode:  "0A0F1A",
  teal:    "0891B2",
  cyan:    "06B6D4",
  emerald: "10B981",
  amber:   "F59E0B",
  red:     "EF4444",
  purple:  "8B5CF6",
  white:   "F1F5F9",
  gray:    "94A3B8",
  grayLt:  "CBD5E1",
};
const FONT = { header: "Arial", body: "Arial" };
const mkShadow = () => ({ type: "outer", blur: 6, offset: 2, color: "000000", opacity: 0.25 });
const edgePad = 0.6;

// ═══════════════════════════════════════════
// SLIDE 1 — TITLE
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: "060E1E" };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.05, fill: { color: C.teal } });
  s.addText("通睿 AI 安全网关", { x: edgePad, y: 1.4, w: 8.8, h: 0.9, fontSize: 44, fontFace: FONT.header, color: C.white, bold: true });
  s.addText("技术架构白皮书", { x: edgePad, y: 2.4, w: 8.8, h: 0.6, fontSize: 24, fontFace: FONT.body, color: C.teal });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 3.2, w: 2.0, h: 0.03, fill: { color: C.gray } });
  s.addText("版本 V4.0 · 2026-05-23 · Confidential", { x: edgePad, y: 3.5, w: 8.8, h: 0.4, fontSize: 13, fontFace: FONT.body, color: C.gray });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.4, w: 10, h: 0.05, fill: { color: C.gray } });
})();

// ═══════════════════════════════════════════
// SLIDE 2 — 产品定位
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("产品定位与技术概览", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // Core definition
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.15, w: 8.8, h: 0.75, fill: { color: C.bgCard } });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.15, w: 0.05, h: 0.75, fill: { color: C.teal } });
  s.addText("通睿是一个多节点协同的隐私计算中间件。每个参与方在自己的防火墙内部署\n一个网关节点，节点在本地完成数据读取、分析与脱敏，仅将脱敏结果发送至\n协调节点聚合。原始数据永不离开各自的可控环境。", { x: edgePad + 0.2, y: 1.2, w: 8.4, h: 0.65, fontSize: 12, fontFace: FONT.body, color: C.grayLt, margin: 0 });

  // Tech stack
  const stack = [
    { layer: "协调节点", tech: "Python FastAPI + PostgreSQL + Redis + mTLS 1.3" },
    { layer: "网关节点", tech: "Python FastAPI + Docker SDK + SQLite（本地）" },
    { layer: "沙箱执行环境", tech: "Docker 容器 · NET=none · 只读挂载 · 2核/4GB" },
    { layer: "脱敏引擎", tech: "正则 + 字段级规则 · 6种脱敏方法 · 暴露级别 L0-L2" },
    { layer: "AI 集成", tech: "GGUF/ONNX 本地推理 · LLM/ML · 输出安全扫描" },
    { layer: "前端控制台", tech: "React + TypeScript · 仪表盘/节点/任务/审计" },
  ];
  stack.forEach((st, i) => {
    const y = 2.2 + i * 0.5;
    s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y, w: 2.5, h: 0.4, fill: { color: C.teal, transparency: 60 } });
    s.addText(st.layer, { x: edgePad + 0.1, y, w: 2.3, h: 0.4, fontSize: 11, fontFace: FONT.header, color: C.white, bold: true, valign: "middle", margin: 0 });
    s.addText(st.tech, { x: edgePad + 2.7, y, w: 6.7, h: 0.4, fontSize: 11, fontFace: FONT.body, color: C.grayLt, valign: "middle", margin: 0 });
    if (i < stack.length - 1) s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: y + 0.43, w: 8.8, h: 0.005, fill: { color: C.gray } });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 3 — 架构全景
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("架构全景图", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // Coordinator
  s.addShape(pres.shapes.RECTANGLE, { x: 2.5, y: 1.2, w: 5.0, h: 0.7, fill: { color: C.teal, transparency: 40 } });
  s.addText("协调节点 (Coordinator)\n任务调度 · 结果聚合 · RBAC · 审计日志", { x: 2.5, y: 1.2, w: 5.0, h: 0.7, fontSize: 12, fontFace: FONT.header, color: C.white, align: "center", valign: "middle", bold: true });

  // Connections
  s.addShape(pres.shapes.LINE, { x: 4.5, y: 1.9, w: 0, h: 0.25, line: { color: C.gray, width: 1 } });
  s.addShape(pres.shapes.LINE, { x: 5.5, y: 1.9, w: 0, h: 0.25, line: { color: C.gray, width: 1 } });
  s.addText("mTLS 1.3 · 端口 8443", { x: 3.0, y: 1.95, w: 4.0, h: 0.3, fontSize: 10, fontFace: FONT.body, color: C.gray, align: "center" });

  // Nodes
  const nodes = ["节点 A\n客户 A 防火墙内", "节点 B\n客户 B 防火墙内", "节点 C\n客户 C 防火墙内"];
  nodes.forEach((n, i) => {
    const x = 0.6 + i * 3.2;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.4, w: 2.8, h: 1.3, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.4, w: 2.8, h: 0.04, fill: { color: C.emerald } });
    s.addText(n, { x, y: 2.55, w: 2.8, h: 0.45, fontSize: 12, fontFace: FONT.header, color: C.emerald, align: "center", bold: true });
    s.addText("Docker 沙箱\n脱敏引擎 · 本地 AI\n只读 /data → 写入 /output", { x: x + 0.1, y: 3.05, w: 2.6, h: 0.55, fontSize: 9, fontFace: FONT.body, color: C.gray, align: "center", margin: 0 });
  });

  // Legend
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 4.0, w: 8.8, h: 1.3, fill: { color: C.bgCard } });
  s.addText("数据流说明", { x: edgePad + 0.15, y: 4.05, w: 3, h: 0.3, fontSize: 13, fontFace: FONT.header, color: C.amber, bold: true });
  const flowItems = [
    "① 原始数据：仅在节点本地 Docker 沙箱中读取（只读挂载，/data/）",
    "② 脱敏结果：经脱敏引擎处理后，加密回传协调节点（mTLS）",
    "③ 聚合报告：协调节点在内存中聚合，结果不落盘（可配）",
    "④ AI 推理：脱敏后的数据输入本地 GGUF/ONNX 模型，原始数据永不进入模型上下文",
  ];
  flowItems.forEach((f, i) => {
    s.addText(f, { x: edgePad + 0.2, y: 4.4 + i * 0.2, w: 8.4, h: 0.2, fontSize: 10, fontFace: FONT.body, color: C.grayLt, margin: 0 });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 4 — 节点生命周期
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("节点生命周期管理", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // State machine
  const states = ["注册", "在线", "执行中", "离线", "注销"];
  states.forEach((st, i) => {
    const x = 0.5 + i * 1.9;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.2, w: 1.6, h: 0.5, fill: { color: i === 1 || i === 2 ? C.emerald : C.bgCard, transparency: i === 1 || i === 2 ? 40 : 0 } });
    s.addText(st, { x, y: 1.2, w: 1.6, h: 0.5, fontSize: 13, fontFace: FONT.header, color: C.white, align: "center", valign: "middle", bold: true });
    if (i < 4) s.addText("→", { x: x + 1.6, y: 1.2, w: 0.3, h: 0.5, fontSize: 16, color: C.gray, align: "center", valign: "middle" });
  });

  // Detail cards
  const details = [
    { title: "注册流程", items: ["验证 SSL 证书 → 分配 node_id → 建立 mTLS → 返回令牌", "证书无效 → 401", "名称重复 → 409"] },
    { title: "心跳机制", items: ["每 30s 发送: {node_id, timestamp, status, load_avg, disk_usage}", "连续 3 次无心跳 → 标记 OFFLINE → 通知管理员"] },
    { title: "并发控制", items: ["单节点最大并发任务数: 3", "超出排队，FIFO", "max_cpu_cores: 2 · max_memory_mb: 4096"] },
    { title: "注销流程", items: ["前置条件: 无进行中任务", "撤销 mTLS 证书 → 清理路由表 → 归档审计日志", "节点本地数据由客户自行处置"] },
  ];
  details.forEach((d, i) => {
    const x = edgePad + (i % 2) * 4.5;
    const y = 2.0 + Math.floor(i / 2) * 1.65;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.2, h: 1.45, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.2, h: 0.04, fill: { color: C.teal } });
    s.addText(d.title, { x: x + 0.12, y: y + 0.08, w: 4, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    d.items.forEach((item, j) => {
      s.addText("▸ " + item, { x: x + 0.15, y: y + 0.45 + j * 0.3, w: 3.9, h: 0.28, fontSize: 10, fontFace: FONT.body, color: C.grayLt, margin: 0 });
    });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 5 — 任务生命周期
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("分析任务生命周期", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // State machine flow
  const flow = [
    { state: "PENDING", desc: "创建", color: C.gray },
    { state: "VALIDATING", desc: "校验节点+脚本+权限", color: C.amber },
    { state: "DISPATCHING", desc: "加密分发到节点", color: C.amber },
    { state: "RUNNING", desc: "沙箱执行", color: C.cyan },
    { state: "AGGREGATING", desc: "聚合结果", color: C.cyan },
    { state: "COMPLETED", desc: "完成", color: C.emerald },
  ];
  flow.forEach((f, i) => {
    const x = 0.3 + i * 1.6;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.2, w: 1.35, h: 0.55, fill: { color: f.color, transparency: 60 } });
    s.addText(f.state, { x, y: 1.2, w: 1.35, h: 0.3, fontSize: 9, fontFace: FONT.header, color: C.white, align: "center", valign: "middle", bold: true });
    s.addText(f.desc, { x, y: 1.48, w: 1.35, h: 0.2, fontSize: 8, fontFace: FONT.body, color: C.grayLt, align: "center", margin: 0 });
    if (i < 5) s.addText("→", { x: x + 1.35, y: 1.2, w: 0.25, h: 0.55, fontSize: 14, color: C.gray, align: "center", valign: "middle" });
  });

  // Error paths
  s.addShape(pres.shapes.LINE, { x: 5.4, y: 1.48, w: 0, h: 0.3, line: { color: C.red, width: 1 } });
  s.addText("PARTIAL\n(部分节点失败)", { x: 4.7, y: 1.8, w: 1.5, h: 0.5, fontSize: 9, fontFace: FONT.body, color: C.red, align: "center", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 7.2, y: 1.48, w: 0, h: 0.3, line: { color: C.red, width: 1 } });
  s.addText("FAILED / TIMEOUT\n(全部失败/超时)", { x: 6.4, y: 1.8, w: 1.6, h: 0.5, fontSize: 9, fontFace: FONT.body, color: C.red, align: "center", margin: 0 });

  // Task detail specs
  s.addText("任务结构", { x: edgePad, y: 2.5, w: 4, h: 0.35, fontSize: 16, fontFace: FONT.header, color: C.amber, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 2.9, w: 8.8, h: 2.4, fill: { color: C.bgCode } });
  s.addText([
    { text: "{\n", options: { color: C.gray, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "task_id": "uuid",\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "workflow": "parallel|sequential",\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "timeout_seconds": 300,\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "target_nodes": ["node-a", "node-b"],\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "required_exposure_level": "L0|L1|L2",\n', options: { color: C.amber, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "script_id": "sha256:abc123...",\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "completeness_score": 0-100,\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '  "steps": [\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '    { "node_id", "status", "execution_time_ms",\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '      "result": {...}, "sanitization_log": [...] }\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '  ]\n', options: { color: C.grayLt, fontSize: 9, fontFace: "Consolas" } },
    { text: '}', options: { color: C.gray, fontSize: 9, fontFace: "Consolas" } },
  ], { x: edgePad + 0.15, y: 2.95, w: 8.5, h: 2.3, margin: 0, valign: "top" });
})();

// ═══════════════════════════════════════════
// SLIDE 6 — 脱敏引擎
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("脱敏引擎详解", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // 6 methods table
  const methods = [
    ["方法", "适用数据", "变换方式", "可逆性"],
    ["pseudonymize", "企业名 / 人名", "→ 临时 Token（跨任务一致）", "不可逆"],
    ["mask", "手机号 / 账号 / 身份证", "→ 首尾各保留 2 位，中间 ****", "不可逆"],
    ["bucket", "营收 / 金额 / 电量", "→ 高/中/低 或 区间 A/B/C", "不可逆"],
    ["generalize", "地址 / GPS 坐标", "→ 区县级 / 1km 网格中心", "不可逆"],
    ["aggregate", "数值型指标", "→ 均值 / 中位数 / 标准差", "不可逆"],
    ["k_anonymize", "多字段组合", "→ 任意组合至少出现 k 次", "不可逆"],
  ];
  s.addTable(methods, {
    x: edgePad, y: 1.15, w: 8.8,
    colW: [1.5, 2.2, 3.3, 0.8],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.35, 0.32, 0.32, 0.32, 0.32, 0.32, 0.32],
    fontFace: FONT.body,
    fontSize: 9,
    color: C.grayLt,
    autoPage: false,
  });
  // Style header row
  for (let c = 0; c < 4; c++) {
    methods[0][c] = { text: methods[0][c], options: { bold: true, color: C.white, fill: { color: C.teal }, fontSize: 10 } };
  }
  // Alternating row fills
  for (let r = 1; r < 7; r++) {
    for (let c = 0; c < 4; c++) {
      methods[r][c] = { text: methods[r][c], options: { fill: { color: r % 2 === 0 ? C.bgCard : C.bg }, fontSize: 9 } };
    }
  }

  // Execution pipeline
  s.addText("脱敏执行管道", { x: edgePad, y: 3.65, w: 4, h: 0.35, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const pipeline = [
    "脚本写入 /output/ ──→ 网关拦截层",
    "字段 × 脱敏规则匹配 ──→ 优先级: 精确 > 类型 > 正则",
    "执行脱敏变换 ──→ 生成 sanitization_log",
    "白名单放行 / 默认拦截 ──→ 实际写入",
  ];
  pipeline.forEach((step, i) => {
    const sx = edgePad + (i % 2) * 4.5;
    const sy = 4.1 + Math.floor(i / 2) * 0.45;
    s.addShape(pres.shapes.RECTANGLE, { x: sx, y: sy, w: 4.2, h: 0.38, fill: { color: C.bgCard } });
    s.addShape(pres.shapes.OVAL, { x: sx + 0.08, y: sy + 0.07, w: 0.22, h: 0.22, fill: { color: C.teal } });
    s.addText(String(i + 1), { x: sx + 0.08, y: sy + 0.07, w: 0.22, h: 0.22, fontSize: 9, fontFace: FONT.header, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(step, { x: sx + 0.4, y: sy + 0.02, w: 3.6, h: 0.35, fontSize: 10, fontFace: FONT.body, color: C.grayLt, margin: 0, valign: "middle" });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 7 — 暴露级别
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("暴露级别控制与沙箱环境", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // Exposure levels
  const levels = [
    { level: "L0", title: "仅数值评分", desc: "0-100 健康分", ex: "供应链评估", color: C.emerald },
    { level: "L1", title: "+聚合统计", desc: "均值/分位数/标准差", ex: "行业对标", color: C.cyan },
    { level: "L2", title: "+脱敏实体", desc: "脱敏后实体级数据", ex: "联合风控", color: C.amber },
  ];
  levels.forEach((l, i) => {
    const x = edgePad + i * 3.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.15, w: 2.85, h: 1.45, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.15, w: 2.85, h: 0.04, fill: { color: l.color } });
    s.addText(l.level, { x: x + 0.1, y: 1.25, w: 0.5, h: 0.4, fontSize: 24, fontFace: FONT.header, color: l.color, bold: true, margin: 0 });
    s.addText(l.title, { x: x + 0.6, y: 1.28, w: 2.1, h: 0.3, fontSize: 16, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(l.desc, { x: x + 0.1, y: 1.75, w: 2.65, h: 0.25, fontSize: 11, fontFace: FONT.body, color: C.gray, margin: 0 });
    s.addText("场景: " + l.ex, { x: x + 0.1, y: 2.1, w: 2.65, h: 0.25, fontSize: 10, fontFace: FONT.body, color: C.grayLt, margin: 0 });
  });

  // Hard constraint
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 2.8, w: 8.8, h: 0.45, fill: { color: C.red, transparency: 70 } });
  s.addText("⚡ 安全硬约束：节点配置暴露级别 < 任务要求 → 立即拒绝 (403) → 明确返回差异信息", { x: edgePad + 0.15, y: 2.82, w: 8.5, h: 0.4, fontSize: 11, fontFace: FONT.header, color: C.white, margin: 0, valign: "middle" });

  // Sandbox specs
  s.addText("Docker 沙箱隔离规格", { x: edgePad, y: 3.45, w: 5, h: 0.35, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const sandbox = [
    ["挂载", "/data/ (只读)", "/output/ (写入拦截)", "—"],
    ["网络", "NET=none", "DNS 无", "完全隔离"],
    ["资源", "CPU 2核", "内存 4GB", "超时 300s"],
    ["安全", "read-only rootfs", "no-new-privileges", "禁止子进程"],
    ["禁止", "网络出站", "特权模式", "exec/eval"],
  ];
  s.addTable(sandbox, {
    x: edgePad, y: 3.85, w: 8.8,
    colW: [1.0, 2.4, 2.6, 2.0],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.25, 0.25, 0.25, 0.25, 0.25],
    fontFace: FONT.body,
    fontSize: 9,
    color: C.grayLt,
  });
  // Style
  sandbox[0] = sandbox[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.teal }, fontSize: 9 } }));
})();

// ═══════════════════════════════════════════
// SLIDE 8 — 威胁模型
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("安全架构：威胁模型", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.red } });

  const threats = [
    ["威胁", "攻击者", "等级", "防御"],
    ["恶意脚本窃取数据", "发起人", "🔴 高", "沙箱隔离 + 白名单 + 脱敏拦截 + 代码审查"],
    ["节点伪造", "外部攻击", "🟠 中", "mTLS 双向证书 + JWT 绑定 node_id"],
    ["中间人拦截", "网络攻击", "🟡 中低", "TLS 1.3 + Certificate Pinning"],
    ["管理员偷看脱敏输出", "内部人员", "🟠 中", "RBAC + 审计不可删除 + 输出本身已脱敏"],
    ["重放攻击", "外部攻击", "🟡 中低", "JWT nonce + timestamp + 服务端去重"],
    ["脱敏规则被篡改", "节点管理员", "🟠 中", "变更审批 + 审计记录变更前后对比"],
    ["侧信道攻击", "高级攻击", "🟡 中低", "统一错误格式 + 随机化处理时间"],
    ["AI 模型反推数据", "模型使用者", "🟡 中", "输出二次校验 + 脱敏数据本身不可还原"],
  ];
  s.addTable(threats, {
    x: edgePad, y: 1.15, w: 8.8,
    colW: [2.0, 1.5, 0.9, 4.4],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.3, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42],
    fontFace: FONT.body,
    fontSize: 9,
    color: C.grayLt,
  });
  // Header
  threats[0] = threats[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.red }, fontSize: 10 } }));
  // Row styling
  for (let r = 1; r < 9; r++) {
    for (let c = 0; c < 4; c++) {
      threats[r][c] = { text: threats[r][c], options: { fill: { color: r % 2 === 0 ? C.bgCard : C.bg }, fontSize: 9, color: c === 2 ? (threats[r][2] && threats[r][2].includes("高") ? C.red : C.amber) : C.grayLt } };
    }
  }
})();

// ═══════════════════════════════════════════
// SLIDE 9 — 纵深防御
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("安全架构：纵深防御六层", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.red } });

  const layers = [
    { n: "L1", title: "网络隔离", desc: "沙箱 NET=none", detail: "无 DNS · 无出站 · 无法外发任何数据", color: C.red },
    { n: "L2", title: "文件系统控制", desc: "只读 + 写入拦截", detail: "只读挂载数据源 · 输出写入经过网关拦截层 · 白名单放行", color: "F97316" },
    { n: "L3", title: "脱敏引擎", desc: "字段级规则", detail: "精确/类型/正则匹配 · 6种脱敏方法 · 未匹配=默认拦截", color: C.amber },
    { n: "L4", title: "输出校验", desc: "脱敏日志 + 内容扫描", detail: "sanitization_log · 正则检测原始数据模式 · 双向校验", color: C.emerald },
    { n: "L5", title: "传输加密", desc: "mTLS 1.3", detail: "端到端加密 · 单一端口 8443 · 自签 CA + CRL · 证书固定", color: C.cyan },
    { n: "L6", title: "审计追溯", desc: "全链路日志 + HMAC", detail: "不可删除 · SHA256-HMAC 防篡改 · 保留 90 天 · 支持 SIEM 导出", color: C.purple },
  ];
  layers.forEach((l, i) => {
    const y = 1.2 + i * 0.7;
    // Layer number badge
    s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y, w: 0.55, h: 0.55, fill: { color: l.color, transparency: 40 } });
    s.addText(l.n, { x: edgePad, y, w: 0.55, h: 0.55, fontSize: 16, fontFace: FONT.header, color: l.color, align: "center", valign: "middle", bold: true });
    // Content
    s.addShape(pres.shapes.RECTANGLE, { x: edgePad + 0.7, y, w: 8.1, h: 0.55, fill: { color: C.bgCard } });
    s.addShape(pres.shapes.RECTANGLE, { x: edgePad + 0.7, y, w: 0.04, h: 0.55, fill: { color: l.color } });
    s.addText(l.title, { x: edgePad + 0.9, y: y + 0.02, w: 3.0, h: 0.25, fontSize: 14, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(l.detail, { x: edgePad + 0.9, y: y + 0.28, w: 7.7, h: 0.22, fontSize: 10, fontFace: FONT.body, color: C.grayLt, margin: 0 });
    s.addText(l.desc, { x: edgePad + 3.9, y: y + 0.02, w: 4.8, h: 0.22, fontSize: 10, fontFace: FONT.body, color: C.gray, margin: 0, align: "right" });
  });

  // Data lifecycle
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 5.3, w: 8.8, h: 0.02, fill: { color: C.gray } });
  s.addText("数据生命周期:  读取(只读挂载) → 处理(沙箱) → 脱敏(网关拦截) → 传输(mTLS) → 聚合(内存) → 销毁(容器清除)", { x: edgePad, y: 5.37, w: 8.8, h: 0.2, fontSize: 9, fontFace: FONT.body, color: C.gray, align: "center" });
})();

// ═══════════════════════════════════════════
// SLIDE 10 — 信任机制
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("信任与透明机制", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.emerald } });

  // 4 pillars
  const pillars = [
    { title: "gateway-verify CLI", desc: "一键环境安全检查。验证沙箱隔离、网络策略、脱敏规则生效。输出通过/不通过明细。" },
    { title: "网络抓包验证脚本", desc: "节点侧 tcpdump 抓包。验证仅有到协调节点的加密 mTLS 流量，无明文/无其他目的地。" },
    { title: "脱敏预览工具", desc: "客户上传样本 CSV → 本地预览脱敏效果 → 确认无误后加入协作。执行前后一致性保证。" },
    { title: "审计日志独立验证", desc: "完整操作链路可导出 → HMAC-SHA256 签名 → 客户/第三方审计独立验证。不可篡改。" },
  ];
  pillars.forEach((p, i) => {
    const x = edgePad + (i % 2) * 4.5;
    const y = 1.2 + Math.floor(i / 2) * 1.25;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.2, h: 1.05, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.05, h: 1.05, fill: { color: C.emerald } });
    s.addText("0" + (i + 1), { x: x + 0.15, y: y + 0.05, w: 0.4, h: 0.35, fontSize: 20, fontFace: FONT.header, color: C.emerald, bold: true, margin: 0 });
    s.addText(p.title, { x: x + 0.6, y: y + 0.08, w: 3.4, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(p.desc, { x: x + 0.15, y: y + 0.5, w: 3.9, h: 0.5, fontSize: 10, fontFace: FONT.body, color: C.grayLt, margin: 0 });
  });

  // Privacy dashboard
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 3.85, w: 8.8, h: 1.45, fill: { color: C.bgCard } });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 3.85, w: 8.8, h: 0.04, fill: { color: C.amber } });
  s.addText("🔒 隐私仪表盘 (每节点独立)", { x: edgePad + 0.15, y: 3.93, w: 5, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const dashItems = [
    "本次任务：哪些字段被读取 / 被哪种方法脱敏 / 脱敏前后指纹 / 输出预览",
    "历史审计：所有任务的数据流向图，每个字段的完整变形链路",
    "风险评估：结合脱敏强度 + 暴露级别 + 协作历史的综合隐私评分",
    "一键退出：任何时候可撤销协作授权，系统立即停止接受该节点的新任务",
  ];
  dashItems.forEach((item, i) => {
    s.addText("▸ " + item, { x: edgePad + 0.2, y: 4.35 + i * 0.22, w: 8.4, h: 0.2, fontSize: 10, fontFace: FONT.body, color: C.grayLt, margin: 0 });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 11 — AI 集成
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("AI 模型集成方案", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.cyan } });

  // Pipeline
  s.addText("AI 数据处理管道", { x: edgePad, y: 1.1, w: 4, h: 0.35, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const pipe = ["原始数据库", "网关节点\n本地读取", "脱敏引擎\napply_sanitization()", "AI 模型推理\ngateway.infer()", "输出校验\n正则扫描", "回传协调节点"];
  pipe.forEach((step, i) => {
    const x = edgePad + i * 1.5;
    const isAI = i === 3;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.6, w: 1.35, h: 0.7, fill: { color: isAI ? C.cyan : C.bgCard, transparency: isAI ? 40 : 0 } });
    s.addText(step, { x, y: 1.6, w: 1.35, h: 0.7, fontSize: 9, fontFace: FONT.body, color: isAI ? C.white : C.grayLt, align: "center", valign: "middle", bold: isAI });
    if (i < 5) s.addText("→", { x: x + 1.35, y: 1.6, w: 0.25, h: 0.7, fontSize: 14, color: C.gray, align: "center", valign: "middle" });
  });

  // Key principle
  s.addShape(pres.shapes.RECTANGLE, { x: 1.5, y: 2.55, w: 7.0, h: 0.4, fill: { color: C.red, transparency: 70 } });
  s.addText("⚡ 核心原则：AI 模型永远只接收脱敏后的数据。原始数据永不进入模型上下文。", { x: 1.5, y: 2.55, w: 7.0, h: 0.4, fontSize: 11, fontFace: FONT.header, color: C.white, align: "center", valign: "middle" });

  // Model types table
  const models = [
    ["模型类型", "部署位置", "用途", "数据安全"],
    ["节点侧 LLM (GGUF)", "网关节点本地", "脱敏结果分析摘要/趋势描述", "脱敏数据不出节点"],
    ["节点侧 ML (ONNX/sklearn)", "网关节点本地", "评分/分类/异常检测", "沙箱内推理"],
    ["协调节点 LLM", "协调节点", "聚合结果解读/报告生成", "输入已是脱敏数据"],
    ["外部 LLM API", "云端（可选）", "报告润色", "仅 L0 纯评分允许"],
  ];
  s.addTable(models, {
    x: edgePad, y: 3.15, w: 8.8,
    colW: [2.2, 1.8, 2.5, 2.3],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.3, 0.32, 0.32, 0.32, 0.32],
    fontFace: FONT.body,
    fontSize: 9,
    color: C.grayLt,
  });
  models[0] = models[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.cyan }, fontSize: 10 } }));

  // AI security constraints
  s.addText("AI 安全约束", { x: edgePad, y: 4.55, w: 4, h: 0.3, fontSize: 13, fontFace: FONT.header, color: C.amber, bold: true });
  const aiConstraints = [
    "脱敏先行：必须在 apply_sanitization() 后调用 infer()",
    "提示词扫描：检测 prompt 中「解密/还原/原始数据」等绕过语 → 拒绝",
    "输出二次校验：正则扫描 AI 输出中是否含身份证号/手机号格式",
    "模型隔离：沙箱内模型 NET=none，防止隐蔽通道外泄",
  ];
  aiConstraints.forEach((c, i) => {
    s.addText("▸ " + c, { x: edgePad + 0.1, y: 4.85 + i * 0.18, w: 8.6, h: 0.18, fontSize: 9, fontFace: FONT.body, color: C.grayLt, margin: 0 });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 12 — 部署架构
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("部署架构：混合模式", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // Comparison table
  const comp = [
    ["维度", "SaaS 协调节点", "私有化协调节点"],
    ["适用客户", "中小企业 / 多方协作", "大型集团 / 高合规行业"],
    ["运维责任", "通睿负责", "客户 IT 负责"],
    ["数据流", "脱敏结果 → 通睿云", "脱敏结果 → 客户内网"],
    ["租户模式", "多租户逻辑隔离", "天然单租户"],
    ["计费方式", "按量计费", "年订阅制"],
    ["合规认证", "SOC2 + 等保三级", "客户自行合规"],
  ];
  s.addTable(comp, {
    x: edgePad, y: 1.15, w: 8.8,
    colW: [1.6, 3.6, 3.6],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.3, 0.32, 0.32, 0.32, 0.32, 0.32, 0.32],
    fontFace: FONT.body,
    fontSize: 10,
    color: C.grayLt,
  });
  comp[0] = comp[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.teal }, fontSize: 10 } }));

  // Node requirements
  s.addText("节点部署要求", { x: edgePad, y: 3.65, w: 4, h: 0.35, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const reqs = [
    ["项目", "最低配置", "推荐配置"],
    ["OS", "Ubuntu 20.04+ / CentOS 8+", "Ubuntu 22.04 LTS"],
    ["CPU", "2 核", "4 核+"],
    ["内存", "4 GB", "8 GB+"],
    ["磁盘", "10 GB（不含数据源）", "20 GB+"],
    ["网络", "出站 443/8443", "—"],
    ["容器引擎", "Docker 24+ / Podman 4+", "Docker 26+"],
    ["部署", "docker-compose up -d", "一键启动"],
  ];
  s.addTable(reqs, {
    x: edgePad, y: 4.05, w: 8.8,
    colW: [1.5, 3.5, 3.8],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.22, 0.22, 0.22, 0.22, 0.22, 0.22, 0.22, 0.22],
    fontFace: FONT.body,
    fontSize: 9,
    color: C.grayLt,
  });
  reqs[0] = reqs[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.teal }, fontSize: 9 } }));
})();

// ═══════════════════════════════════════════
// SLIDE 13 — API 端点
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("API 端点设计", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // Node API
  s.addText("节点 API（节点 → 协调节点 · mTLS 认证）", { x: edgePad, y: 1.1, w: 6, h: 0.3, fontSize: 12, fontFace: FONT.header, color: C.amber, bold: true });
  const nodeAPI = [
    ["POST", "/api/v1/nodes/register", "节点注册"],
    ["GET", "/api/v1/nodes/{id}/tasks/pending", "拉取待执行任务"],
    ["POST", "/api/v1/nodes/{id}/tasks/{step}/result", "提交脱敏结果"],
    ["POST", "/api/v1/nodes/{id}/heartbeat", "心跳上报"],
    ["DELETE", "/api/v1/nodes/{id}", "节点注销"],
  ];
  s.addTable(nodeAPI, {
    x: edgePad, y: 1.45, w: 8.8,
    colW: [1.0, 4.5, 3.3],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.22, 0.22, 0.22, 0.22, 0.22],
    fontFace: "Consolas",
    fontSize: 8,
    color: C.grayLt,
  });
  for (let r = 0; r < 5; r++) {
    nodeAPI[r][0] = { text: nodeAPI[r][0], options: { color: nodeAPI[r][0] === "POST" ? C.emerald : nodeAPI[r][0] === "DELETE" ? C.red : C.cyan, fontSize: 8 } };
  }

  // User API
  s.addText("用户 API（JWT Bearer 认证）", { x: edgePad, y: 2.8, w: 5, h: 0.3, fontSize: 12, fontFace: FONT.header, color: C.amber, bold: true });
  const userAPI = [
    ["POST", "/api/v1/auth/login", "用户登录"],
    ["POST", "/api/v1/tasks", "创建分析任务"],
    ["GET", "/api/v1/tasks/{id}", "任务详情"],
    ["GET", "/api/v1/tasks/{id}/report", "聚合报告"],
    ["POST", "/api/v1/scripts", "上传分析脚本"],
    ["GET", "/api/v1/nodes/{id}/exposure", "查看节点暴露级别"],
    ["GET", "/api/v1/audit-logs", "审计日志查询"],
  ];
  s.addTable(userAPI, {
    x: edgePad, y: 3.15, w: 8.8,
    colW: [1.0, 3.8, 4.0],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.22, 0.22, 0.22, 0.22, 0.22, 0.22, 0.22],
    fontFace: "Consolas",
    fontSize: 8,
    color: C.grayLt,
  });
  for (let r = 0; r < 7; r++) {
    userAPI[r][0] = { text: userAPI[r][0], options: { color: userAPI[r][0] === "POST" ? C.emerald : C.cyan, fontSize: 8 } };
  }

  // Local API
  s.addText("节点本地 API（仅 mTLS 内部调用）", { x: edgePad, y: 4.95, w: 5, h: 0.25, fontSize: 11, fontFace: FONT.header, color: C.gray, bold: true });
  s.addText("POST /local/v1/execute   ·   PUT /local/v1/rules   ·   POST /local/v1/models   ·   GET /local/v1/health   ·   GET /local/v1/metrics", { x: edgePad, y: 5.2, w: 8.8, h: 0.2, fontSize: 9, fontFace: "Consolas", color: C.grayLt });
})();

// ═══════════════════════════════════════════
// SLIDE 14 — 非功能需求
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("非功能需求与性能指标", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.teal } });

  // Performance
  s.addText("性能指标", { x: edgePad, y: 1.1, w: 3, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const perf = [
    ["指标", "目标值"],
    ["节点注册完成时间", "≤ 10 秒"],
    ["任务分发延迟（10节点）", "≤ 5 秒"],
    ["单节点脚本执行（不含AI）", "≤ 30 秒"],
    ["脱敏引擎吞吐量", "≥ 10,000 字段/秒"],
    ["协调节点 API P99 延迟", "≤ 500ms"],
    ["并发任务支持", "≥ 50 个"],
  ];
  s.addTable(perf, {
    x: edgePad, y: 1.45, w: 4.2,
    colW: [2.5, 1.7],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.25, 0.22, 0.22, 0.22, 0.22, 0.22, 0.22],
    fontFace: FONT.body, fontSize: 9, color: C.grayLt,
  });
  perf[0] = perf[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.teal }, fontSize: 9 } }));

  // Availability
  s.addText("可用性 & 扩展性", { x: 5.2, y: 1.1, w: 3, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const avail = [
    ["指标", "目标值"],
    ["协调节点可用性", "99.9% (月宕机 ≤43min)"],
    ["节点离线容忍", "部分离线不影响其他"],
    ["优雅降级", "PARTIAL 而非 FAILED"],
    ["支持节点数", "100+ 节点"],
    ["DR 恢复时间", "RTO ≤ 30 分钟"],
  ];
  s.addTable(avail, {
    x: 5.2, y: 1.45, w: 4.2,
    colW: [2.0, 2.2],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.25, 0.22, 0.22, 0.22, 0.22, 0.22],
    fontFace: FONT.body, fontSize: 9, color: C.grayLt,
  });
  avail[0] = avail[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.teal }, fontSize: 9 } }));

  // Compliance
  s.addText("合规与运维", { x: edgePad, y: 3.35, w: 4, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  const compliance = [
    ["标准", "要求"],
    ["等保", "协调节点（SaaS）通过等保三级"],
    ["个保法", "脱敏方案符合个人信息保护法"],
    ["数据跨境", "节点部署地 = 数据存储地"],
    ["国密", "SM2/SM4 可选（私有化部署）"],
    ["渗透测试", "每季度第三方渗透测试"],
    ["审计日志", "保留 90 天，HMAC 防篡改"],
    ["监控", "Prometheus + Grafana + 告警"],
  ];
  s.addTable(compliance, {
    x: edgePad, y: 3.7, w: 8.8,
    colW: [1.5, 7.3],
    border: { pt: 0.5, color: C.gray },
    rowH: [0.22, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
    fontFace: FONT.body, fontSize: 9, color: C.grayLt,
  });
  compliance[0] = compliance[0].map(t => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.teal }, fontSize: 9 } }));
})();

// ═══════════════════════════════════════════
// SLIDE 15 — 验收标准
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("验收标准", { x: edgePad, y: 0.25, w: 8.8, h: 0.6, fontSize: 28, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 0.9, w: 1.0, h: 0.03, fill: { color: C.emerald } });

  // Functional AC
  s.addText("功能验收（8 项）", { x: edgePad, y: 1.1, w: 4, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.emerald, bold: true });
  const funcAC = [
    "AC-1  一键部署：docker-compose up → 30s 内控制台可访问",
    "AC-2  多节点协作：2 节点任务 → 本地执行 → 脱敏聚合 → 原始数据未出域",
    "AC-3  脱敏效果：entity_name 伪名化 + revenue 分档 → 抓包验证原始值不出现",
    "AC-4  离线容错：节点离线 → PARTIAL → completeness_score 正确",
    "AC-5  审计完整性：3 个任务 → 导出全链路日志 → HMAC 验证通过",
    "AC-6  安全拦截：无证书连接拒绝 · 无权限任务 403",
    "AC-7  AI 调用：gateway.infer() → 仅传入脱敏数据 → 输出不含原始数据",
    "AC-8  暴露级别约束：L0节点拒绝L2任务 → 403 + 明确错误信息",
  ];
  funcAC.forEach((ac, i) => {
    s.addText(ac, { x: edgePad + 0.1, y: 1.45 + i * 0.28, w: 8.7, h: 0.25, fontSize: 9, fontFace: "Consolas", color: C.grayLt, margin: 0 });
  });

  // Trust AC
  s.addText("信任验收（5 项 · 客户视角）", { x: edgePad, y: 3.85, w: 5, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.cyan, bold: true });
  const trustAC = [
    "AC-9  客户自验证：运行 gateway-verify → 所有检查通过",
    "AC-10 脱敏预览：上传样本 → 预览效果 → 与实际执行一致",
    "AC-11 抓包透明：节点侧抓包 → 仅见加密 mTLS 流量",
    "AC-12 隐私仪表盘：任务完成后 → 完整脱敏日志可逐条比对",
    "AC-13 审计导出：第三方独立验证 HMAC 签名完整性",
  ];
  trustAC.forEach((ac, i) => {
    s.addText(ac, { x: edgePad + 0.1, y: 4.2 + i * 0.28, w: 8.7, h: 0.25, fontSize: 9, fontFace: "Consolas", color: C.grayLt, margin: 0 });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 16 — CLOSING
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: "060E1E" };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.05, fill: { color: C.teal } });
  s.addText("技术架构白皮书 · V4.0", { x: 0.8, y: 0.5, w: 8.4, h: 0.4, fontSize: 13, fontFace: FONT.body, color: C.gray, align: "center" });
  s.addText("通睿 AI 安全网关", { x: 0.8, y: 1.5, w: 8.4, h: 0.8, fontSize: 36, fontFace: FONT.header, color: C.white, bold: true, align: "center" });
  s.addText("数据不出域，价值无边界", { x: 0.8, y: 2.4, w: 8.4, h: 0.5, fontSize: 20, fontFace: FONT.body, color: C.teal, align: "center", italic: true });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.5, y: 3.15, w: 3.0, h: 0.03, fill: { color: C.gray } });

  const items = [
    "完整 SRS 文档：产品需求规格说明书_V4.md",
    "下一步：SDD 技术设计阶段",
  ];
  items.forEach((item, i) => {
    s.addText("▸ " + item, { x: 2.5, y: 3.4 + i * 0.35, w: 5.0, h: 0.3, fontSize: 12, fontFace: FONT.body, color: C.grayLt, align: "center" });
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.4, w: 10, h: 0.05, fill: { color: C.gray } });
})();

// ── Output ──
pres.writeFile({ fileName: "/home/jipin/ai-security-gateway/ppt/通睿AI安全网关_技术架构版.pptx" })
  .then(() => console.log("✓ Technical PPT generated"))
  .catch(e => console.error("✗", e));
