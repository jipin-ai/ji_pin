// 通睿 AI 安全网关 — 投资人/客户介绍 PPT
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "通睿科技";
pres.title = "通睿 AI 安全网关 — 产品介绍";

// ── Theme ──
const C = {
  bg:      "0B1120",
  bgCard:  "1E293B",
  bgCard2: "162032",
  cyan:    "06B6D4",
  emerald: "10B981",
  amber:   "F59E0B",
  red:     "EF4444",
  white:   "F1F5F9",
  gray:    "94A3B8",
  grayLt:  "CBD5E1",
};
const FONT = { header: "Arial Black", body: "Arial" };
const mkShadow = () => ({ type: "outer", blur: 8, offset: 3, color: "000000", opacity: 0.3 });
const edgePad = 0.6; // edge padding for slides

// ═══════════════════════════════════════════
// SLIDE 1 — TITLE
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: "060E1E" };
  // decorative top bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.cyan } });
  // brand
  s.addText("通睿科技", { x: edgePad, y: 0.35, w: 3, h: 0.4, fontSize: 13, fontFace: FONT.body, color: C.cyan, bold: true, charSpacing: 4 });
  // main title
  s.addText("通睿 AI 安全网关", { x: edgePad, y: 1.6, w: 8.8, h: 1.2, fontSize: 48, fontFace: FONT.header, color: C.white, bold: true });
  // tagline
  s.addText("数据不出域，价值无边界", { x: edgePad, y: 2.85, w: 8.8, h: 0.7, fontSize: 24, fontFace: FONT.body, color: C.cyan, italic: true });
  // subtitle
  s.addText("隐私计算中间件 · 通用平台 · 混合部署", { x: edgePad, y: 3.6, w: 8.8, h: 0.5, fontSize: 16, fontFace: FONT.body, color: C.gray });
  // bottom bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.3, w: 10, h: 0.06, fill: { color: C.gray } });
  s.addText("2026 · 产品介绍", { x: edgePad, y: 5.15, w: 4, h: 0.35, fontSize: 11, fontFace: FONT.body, color: C.gray });
})();

// ═══════════════════════════════════════════
// SLIDE 2 — 市场机会
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("数据协作的万亿美元悖论", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });
  // Big stat
  s.addText("$11T", { x: edgePad, y: 1.4, w: 3, h: 1.2, fontSize: 60, fontFace: FONT.header, color: C.cyan, bold: true });
  s.addText("全球数据经济总量，\n但 68% 的企业数据从未被利用\n——因为「不敢共享」", { x: edgePad, y: 2.65, w: 4, h: 1.0, fontSize: 14, fontFace: FONT.body, color: C.gray });
  // Right side - paradox
  const cards = [
    { title: "不流通", desc: "数据孤岛，AI 模型缺训练样本，风控精度不足，供应链盲区扩大", color: C.red },
    { title: "流通失控", desc: "原始数据离开可控环境，隐私泄露、合规风险、商业机密暴露", color: C.amber },
    { title: "信任缺失", desc: "多方数据协作的核心障碍不是技术，是「凭什么相信你不会偷看我的数据」", color: C.gray },
  ];
  cards.forEach((c, i) => {
    const y = 1.4 + i * 1.25;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y, w: 4.4, h: 1.05, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y, w: 0.06, h: 1.05, fill: { color: c.color } });
    s.addText(c.title, { x: 5.35, y: y + 0.08, w: 3.8, h: 0.35, fontSize: 15, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(c.desc, { x: 5.35, y: y + 0.45, w: 3.8, h: 0.5, fontSize: 11, fontFace: FONT.body, color: C.gray, margin: 0 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.5, w: 10, h: 0.04, fill: { color: C.gray } });
  s.addText("来源：IDC Global DataSphere, Gartner Data Collaboration Report 2025", { x: edgePad, y: 5.25, w: 5, h: 0.35, fontSize: 9, fontFace: FONT.body, color: C.gray });
})();

// ═══════════════════════════════════════════
// SLIDE 3 — 行业痛点
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("五个行业，同一个困境", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });

  const industries = [
    { icon: "🏭", title: "供应链金融", pain: "供应商不愿暴露真实营收", need: "核心企业要评估整链健康度" },
    { icon: "🏦", title: "联合风控", pain: "银行间不能共享客户清单", need: "欺诈特征需跨机构碰撞" },
    { icon: "🏢", title: "集团管控", pain: "子公司抵触总部数据监控", need: "总部需要汇总经营分析" },
    { icon: "🏥", title: "医疗科研", pain: "患者数据受法规严格限制", need: "多中心研究需统计显著性" },
    { icon: "🔗", title: "产业链协同", pain: "库存/排产数据是商业机密", need: "上下游需协同优化交付" },
  ];
  industries.forEach((ind, i) => {
    const row = Math.floor(i / 3);
    const col = i % 3;
    const x = edgePad + col * 3.05;
    const y = 1.4 + row * 2.0;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.85, h: 1.75, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addText(ind.icon, { x, y: y + 0.1, w: 0.5, h: 0.5, fontSize: 28, align: "center", margin: 0 });
    s.addText(ind.title, { x: x + 0.15, y: y + 0.65, w: 2.5, h: 0.35, fontSize: 16, fontFace: FONT.header, color: C.cyan, bold: true, margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.15, y: y + 1.0, w: 0.3, h: 0.03, fill: { color: C.gray } });
    s.addText([
      { text: "痛点：", options: { bold: true, color: C.red, fontSize: 10, breakLine: false } },
      { text: ind.pain, options: { fontSize: 10, color: C.gray, breakLine: true } },
      { text: "需求：", options: { bold: true, color: C.emerald, fontSize: 10, breakLine: false } },
      { text: ind.need, options: { fontSize: 10, color: C.grayLt } },
    ], { x: x + 0.15, y: y + 1.1, w: 2.55, h: 0.6, margin: 0, valign: "top" });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 4 — 方案对比
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("传统模式 vs 通睿模式", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });

  // LEFT: Traditional
  const Lx = edgePad, Ly = 1.3;
  s.addShape(pres.shapes.RECTANGLE, { x: Lx, y: Ly, w: 4.2, h: 3.8, fill: { color: C.bgCard }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: Lx, y: Ly, w: 4.2, h: 0.5, fill: { color: C.red, transparency: 40 } });
  s.addText("✕ 传统模式", { x: Lx + 0.2, y: Ly + 0.05, w: 3.8, h: 0.4, fontSize: 18, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
  s.addText([
    { text: "原始数据上传到中心平台", options: { fontSize: 13, color: C.gray, breakLine: true } },
    { text: "平台集中存储、分析", options: { fontSize: 13, color: C.gray, breakLine: true } },
    { text: "返回结果给各方", options: { fontSize: 13, color: C.gray, breakLine: true } },
    { text: "", options: { fontSize: 8, breakLine: true } },
    { text: "核心问题：", options: { fontSize: 13, color: C.red, bold: true, breakLine: true } },
    { text: "数据拥有者失去控制权", options: { fontSize: 12, color: C.grayLt, breakLine: true } },
    { text: "信任成本极高，合规风险大", options: { fontSize: 12, color: C.grayLt } },
  ], { x: Lx + 0.25, y: Ly + 0.7, w: 3.7, h: 2.8, margin: 0, valign: "top" });

  // ARROW
  s.addText("→", { x: 4.65, y: 2.7, w: 0.7, h: 0.8, fontSize: 36, fontFace: FONT.header, color: C.cyan, align: "center", bold: true });

  // RIGHT: Tongrui
  const Rx = 5.2, Ry = 1.3;
  s.addShape(pres.shapes.RECTANGLE, { x: Rx, y: Ry, w: 4.2, h: 3.8, fill: { color: C.bgCard }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: Rx, y: Ry, w: 4.2, h: 0.5, fill: { color: C.emerald, transparency: 40 } });
  s.addText("✓ 通睿模式", { x: Rx + 0.2, y: Ry + 0.05, w: 3.8, h: 0.4, fontSize: 18, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
  s.addText([
    { text: "各方本地部署网关节点", options: { fontSize: 13, color: C.gray, breakLine: true } },
    { text: "本地读取 → 本地脱敏 → 仅结果出域", options: { fontSize: 13, color: C.gray, breakLine: true } },
    { text: "协调节点聚合脱敏结果", options: { fontSize: 13, color: C.gray, breakLine: true } },
    { text: "", options: { fontSize: 8, breakLine: true } },
    { text: "核心优势：", options: { fontSize: 13, color: C.emerald, bold: true, breakLine: true } },
    { text: "原始数据永不离开防火墙", options: { fontSize: 12, color: C.grayLt, breakLine: true } },
    { text: "信任由技术保证，非合同约束", options: { fontSize: 12, color: C.grayLt } },
  ], { x: Rx + 0.25, y: Ry + 0.7, w: 3.7, h: 2.8, margin: 0, valign: "top" });
})();

// ═══════════════════════════════════════════
// SLIDE 5 — 五大核心原则
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("五大核心原则", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });

  const principles = [
    { n: "01", title: "数据不出域", desc: "原始数据物理上不离开数据拥有者的网络边界，计算在节点侧本地执行", color: C.cyan },
    { n: "02", title: "最小暴露", desc: "仅传输任务必需的最小化脱敏结果，输出白名单 + 暴露级别双重控制", color: C.emerald },
    { n: "03", title: "可验证安全", desc: "客户可自行抓包验证数据未被泄露，而非仅依赖厂商承诺", color: C.amber },
    { n: "04", title: "价值可量化", desc: "每次协作的价值增量可被双方感知——对比基准、协同增益、贡献权重", color: "8B5CF6" },
    { n: "05", title: "AI 就绪", desc: "脱敏后的数据可直接输入 LLM/ML 模型，实现隐私安全的智能决策", color: "EC4899" },
  ];
  principles.forEach((p, i) => {
    const x = edgePad + (i % 3) * 3.05;
    const y = 1.4 + Math.floor(i / 3) * 2.0;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.85, h: 1.75, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addText(p.n, { x: x + 0.15, y: y + 0.08, w: 0.6, h: 0.5, fontSize: 32, fontFace: FONT.header, color: p.color, bold: true, margin: 0 });
    s.addText(p.title, { x: x + 0.85, y: y + 0.15, w: 1.85, h: 0.4, fontSize: 18, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.15, y: y + 0.75, w: 1.5, h: 0.02, fill: { color: p.color } });
    s.addText(p.desc, { x: x + 0.15, y: y + 0.9, w: 2.55, h: 0.75, fontSize: 11, fontFace: FONT.body, color: C.gray, margin: 0, valign: "top" });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 6 — 场景一：供应链
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.cyan } });
  s.addText("场景", { x: edgePad, y: 0.2, w: 2, h: 0.35, fontSize: 12, fontFace: FONT.body, color: C.cyan, bold: true, charSpacing: 4 });
  s.addText("供应链健康度评估", { x: edgePad, y: 0.6, w: 8.8, h: 0.7, fontSize: 30, fontFace: FONT.header, color: C.white, bold: true });

  // Flow diagram
  const fY = 1.55;
  // Core enterprise
  s.addShape(pres.shapes.RECTANGLE, { x: 4.0, y: fY, w: 2.0, h: 0.7, fill: { color: C.cyan, transparency: 30 } });
  s.addText("核心企业\n发起评估", { x: 4.0, y: fY, w: 2.0, h: 0.7, fontSize: 13, fontFace: FONT.header, color: C.white, align: "center", valign: "middle", bold: true });

  // Suppliers
  const suppliers = ["供应商 A", "供应商 B", "供应商 C", "... 20家"];
  suppliers.forEach((sup, i) => {
    const sx = 0.5 + i * 2.3;
    s.addShape(pres.shapes.RECTANGLE, { x: sx, y: 2.7, w: 2.1, h: 0.55, fill: { color: C.bgCard } });
    s.addShape(pres.shapes.RECTANGLE, { x: sx, y: 2.7, w: 0.06, h: 0.55, fill: { color: C.emerald } });
    s.addText(sup, { x: sx + 0.15, y: 2.7, w: 1.8, h: 0.55, fontSize: 12, fontFace: FONT.body, color: C.white, valign: "middle", margin: 0 });
    s.addText("本地脱敏", { x: sx, y: 3.4, w: 2.1, h: 0.3, fontSize: 10, fontFace: FONT.body, color: C.emerald, align: "center" });
  });

  // Result box
  s.addShape(pres.shapes.RECTANGLE, { x: 2.5, y: 3.95, w: 5.0, h: 1.15, fill: { color: C.bgCard }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 2.5, y: 3.95, w: 5.0, h: 0.04, fill: { color: C.amber } });
  s.addText("聚合报告", { x: 2.7, y: 4.05, w: 4.6, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.amber, bold: true });
  s.addText("供应链健康度 82 分 · 3 家需关注 · 无断供风险\n各供应商营收/客户已脱敏，无法反推原始数据", { x: 2.7, y: 4.35, w: 4.6, h: 0.6, fontSize: 11, fontFace: FONT.body, color: C.grayLt });
})();

// ═══════════════════════════════════════════
// SLIDE 7 — 场景二+三
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("更多应用场景", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });

  // Left: 联合反欺诈
  const Lx = edgePad, Ly = 1.4;
  s.addShape(pres.shapes.RECTANGLE, { x: Lx, y: Ly, w: 4.2, h: 3.5, fill: { color: C.bgCard }, shadow: mkShadow() });
  s.addText("🏦", { x: Lx + 0.2, y: Ly + 0.1, w: 0.5, h: 0.5, fontSize: 28 });
  s.addText("联合反欺诈", { x: Lx + 0.8, y: Ly + 0.15, w: 3, h: 0.4, fontSize: 20, fontFace: FONT.header, color: C.cyan, bold: true, margin: 0 });
  // flow
  const flowItems = [
    "三家银行各自部署网关节点",
    "检查贷款申请的欺诈特征",
    "仅返回 {hit: true/false, fraud_type}",
    "2/3 库命中 → 建议拒绝",
  ];
  flowItems.forEach((item, i) => {
    const iy = Ly + 0.8 + i * 0.6;
    s.addShape(pres.shapes.OVAL, { x: Lx + 0.3, y: iy + 0.1, w: 0.25, h: 0.25, fill: { color: C.emerald } });
    s.addText(String(i + 1), { x: Lx + 0.3, y: iy + 0.08, w: 0.25, h: 0.25, fontSize: 11, fontFace: FONT.header, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(item, { x: Lx + 0.7, y: iy + 0.05, w: 3.2, h: 0.35, fontSize: 12, fontFace: FONT.body, color: C.grayLt, margin: 0 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: Lx + 0.15, y: Ly + 3.2, w: 3.9, h: 0.03, fill: { color: C.gray } });
  s.addText("价值：风控准确率 +18%，联合覆盖盲区客户", { x: Lx + 0.2, y: Ly + 3.3, w: 3.8, h: 0.2, fontSize: 10, fontFace: FONT.body, color: C.amber });

  // Right: 集团经营分析
  const Rx = 5.2, Ry = 1.4;
  s.addShape(pres.shapes.RECTANGLE, { x: Rx, y: Ry, w: 4.2, h: 3.5, fill: { color: C.bgCard }, shadow: mkShadow() });
  s.addText("🏢", { x: Rx + 0.2, y: Ry + 0.1, w: 0.5, h: 0.5, fontSize: 28 });
  s.addText("集团经营分析", { x: Rx + 0.8, y: Ry + 0.15, w: 3, h: 0.4, fontSize: 20, fontFace: FONT.header, color: C.emerald, bold: true, margin: 0 });
  const flowItems2 = [
    "总部发起月度经营分析任务",
    "各子公司节点本地计算 KPI",
    "营收→分档 客户→伪名化",
    "总部看到趋势，无法反推精确数据",
  ];
  flowItems2.forEach((item, i) => {
    const iy = Ry + 0.8 + i * 0.6;
    s.addShape(pres.shapes.OVAL, { x: Rx + 0.3, y: iy + 0.1, w: 0.25, h: 0.25, fill: { color: "8B5CF6" } });
    s.addText(String(i + 1), { x: Rx + 0.3, y: iy + 0.08, w: 0.25, h: 0.25, fontSize: 11, fontFace: FONT.header, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(item, { x: Rx + 0.7, y: iy + 0.05, w: 3.2, h: 0.35, fontSize: 12, fontFace: FONT.body, color: C.grayLt, margin: 0 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: Rx + 0.15, y: Ry + 3.2, w: 3.9, h: 0.03, fill: { color: C.gray } });
  s.addText("价值：子公司安心参与，总部获得全局视野", { x: Rx + 0.2, y: Ry + 3.3, w: 3.8, h: 0.2, fontSize: 10, fontFace: FONT.body, color: C.amber });
})();

// ═══════════════════════════════════════════
// SLIDE 8 — 核心竞争力：信任机制
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("核心竞争力：让安全「看得见」", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.amber } });

  s.addText("不是「说安全」——是让客户「看见安全」", { x: edgePad, y: 2.55, w: 8.8, h: 0.5, fontSize: 16, fontFace: FONT.body, color: C.amber, italic: true, align: "center" });

  // 4-layer pyramid (inverted visual)
  const layers = [
    { level: "L4", title: "监管信任", desc: "第三方审计可验证\nHMAC防篡改日志", color: "8B5CF6" },
    { level: "L3", title: "客户自验证", desc: "提供抓包工具\n客户可自行验证", color: C.cyan },
    { level: "L2", title: "规则透明", desc: "脱敏规则可视化\n全知全控", color: C.emerald },
    { level: "L1", title: "技术强制", desc: "沙箱网络隔离\n白名单拦截\n代码保证", color: C.amber },
  ];
  layers.forEach((l, i) => {
    const w = 1.5 + i * 0.8;
    const x = (10 - w) / 2;
    const y = 0.9 + i * 1.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.95, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.04, fill: { color: l.color } });
    s.addText(l.level, { x: x + 0.15, y: y + 0.08, w: 0.6, h: 0.35, fontSize: 20, fontFace: FONT.header, color: l.color, bold: true, margin: 0 });
    s.addText(l.title, { x: x + 0.85, y: y + 0.08, w: w - 1.2, h: 0.35, fontSize: 16, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(l.desc, { x: x + 0.15, y: y + 0.45, w: w - 0.4, h: 0.45, fontSize: 10, fontFace: FONT.body, color: C.gray, margin: 0 });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 9 — 客户自验证
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("客户自验证工具箱", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.emerald } });

  const tools = [
    { icon: "🔍", title: "gateway-verify CLI", desc: "一键部署验证\n环境安全检查" },
    { icon: "📡", title: "网络抓包验证", desc: "tcpdump 抓包\n确认无明文外泄" },
    { icon: "👁", title: "脱敏预览", desc: "样本数据预览\n执行前后一致" },
    { icon: "📋", title: "审计日志导出", desc: "HMAC 完整性\n独立可验证" },
  ];
  tools.forEach((t, i) => {
    const x = edgePad + i * 2.3;
    const y = 1.4;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.05, h: 1.9, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addText(t.icon, { x, y: y + 0.15, w: 2.05, h: 0.5, fontSize: 30, align: "center", margin: 0 });
    s.addText(t.title, { x: x + 0.1, y: y + 0.7, w: 1.85, h: 0.35, fontSize: 14, fontFace: FONT.header, color: C.cyan, bold: true, align: "center", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.5, y: y + 1.1, w: 1.0, h: 0.02, fill: { color: C.gray } });
    s.addText(t.desc, { x: x + 0.1, y: y + 1.2, w: 1.85, h: 0.6, fontSize: 10, fontFace: FONT.body, color: C.gray, align: "center", margin: 0 });
  });

  // Privacy dashboard highlight
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 3.6, w: 8.8, h: 1.6, fill: { color: C.bgCard2 }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 3.6, w: 0.06, h: 1.6, fill: { color: C.amber } });
  s.addText("🔒 隐私仪表盘", { x: edgePad + 0.25, y: 3.7, w: 4, h: 0.35, fontSize: 16, fontFace: FONT.header, color: C.amber, bold: true, margin: 0 });
  s.addText([
    { text: "每个节点拥有独立的隐私仪表盘：", options: { fontSize: 12, color: C.gray, breakLine: true } },
    { text: "本次任务：哪些字段被读取 / 哪些被脱敏 / 脱敏方法 / 输出内容预览", options: { fontSize: 11, color: C.grayLt, breakLine: true } },
    { text: "历史审计：过去所有任务的数据流向图", options: { fontSize: 11, color: C.grayLt, breakLine: true } },
    { text: "风险评估：结合脱敏强度和暴露级别的隐私风险评分", options: { fontSize: 11, color: C.grayLt, breakLine: true } },
    { text: "一键拒绝：任何时候客户可退出协作网络", options: { fontSize: 11, color: C.red } },
  ], { x: edgePad + 0.25, y: 4.1, w: 8.3, h: 1.0, margin: 0 });
})();

// ═══════════════════════════════════════════
// SLIDE 10 — 价值交换
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("价值交换：协作的正反馈循环", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.emerald } });

  // 4 value dimensions
  const dims = [
    { num: "对比基准", desc: "「您的健康分 82，行业均值 71，\n排名前 20%」" },
    { num: "盲点揭示", desc: "「未覆盖客户群的欺诈风险\n是现有客户的 3.2 倍」" },
    { num: "协同增益", desc: "「结合 5 家合作伙伴数据后，\n风控准确率提升 18%」" },
    { num: "贡献权重", desc: "「您的数据贡献度 35%，\n使结论置信度提升至 92%」" },
  ];
  dims.forEach((d, i) => {
    const x = edgePad + i * 2.3;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.4, w: 2.05, h: 2.0, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addText(d.num, { x: x + 0.1, y: 1.5, w: 1.85, h: 0.4, fontSize: 16, fontFace: FONT.header, color: C.cyan, bold: true, align: "center", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.4, y: 1.95, w: 1.2, h: 0.02, fill: { color: C.gray } });
    s.addText(d.desc, { x: x + 0.1, y: 2.1, w: 1.85, h: 1.1, fontSize: 10, fontFace: FONT.body, color: C.grayLt, align: "center", margin: 0 });
  });

  // Loop diagram
  s.addShape(pres.shapes.RECTANGLE, { x: 1.5, y: 3.7, w: 7.0, h: 1.6, fill: { color: C.bgCard2 } });
  const loop = ["提供脱敏数据", "聚合分析", "获得行业对标", "愿意继续参与"];
  loop.forEach((txt, i) => {
    const lx = 1.8 + i * 1.75;
    s.addShape(pres.shapes.OVAL, { x: lx, y: 3.9, w: 1.3, h: 0.5, fill: { color: C.emerald, transparency: 40 } });
    s.addText(txt, { x: lx, y: 3.9, w: 1.3, h: 0.5, fontSize: 10, fontFace: FONT.header, color: C.white, align: "center", valign: "middle" });
  });
  // arrows
  for (let i = 0; i < 3; i++) {
    s.addText("→", { x: 3.1 + i * 1.75, y: 3.95, w: 0.4, h: 0.4, fontSize: 20, color: C.cyan, align: "center", fontFace: FONT.header, bold: true });
  }
  s.addText("↻ 正反馈循环 → 信任积累 → 暴露级别提升 → 协作价值递增", { x: 1.8, y: 4.55, w: 6.5, h: 0.45, fontSize: 12, fontFace: FONT.body, color: C.cyan, align: "center" });
})();

// ═══════════════════════════════════════════
// SLIDE 11 — 商业模式
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("商业模式与市场定位", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });

  // Two deployment models
  const models = [
    { title: "SaaS 协调节点", sub: "中小企业 / 多方协作", items: ["通睿托管运维", "按量计费", "多租户隔离", "SOC2+等保三级"], accent: C.cyan },
    { title: "私有化协调节点", sub: "大型集团 / 高合规行业", items: ["客户内网部署", "年订阅制", "单租户", "客户自行合规"], accent: C.emerald },
  ];
  models.forEach((m, i) => {
    const x = edgePad + i * 4.5;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.4, w: 4.15, h: 2.2, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.4, w: 4.15, h: 0.55, fill: { color: m.accent, transparency: 60 } });
    s.addText(m.title, { x: x + 0.15, y: 1.42, w: 3, h: 0.35, fontSize: 18, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(m.sub, { x: x + 0.15, y: 1.75, w: 3, h: 0.2, fontSize: 11, fontFace: FONT.body, color: C.gray, margin: 0 });
    m.items.forEach((item, j) => {
      s.addText("✓ " + item, { x: x + 0.2, y: 2.1 + j * 0.32, w: 3.7, h: 0.3, fontSize: 11, fontFace: FONT.body, color: C.grayLt, margin: 0 });
    });
  });

  // Pricing
  s.addText("计费模式（草案）", { x: edgePad, y: 3.9, w: 8.8, h: 0.4, fontSize: 18, fontFace: FONT.header, color: C.white, bold: true });
  const tiers = [
    { name: "基础版", nodes: "5 节点", tasks: "50 任务/月", price: "按年订阅" },
    { name: "专业版", nodes: "20 节点", tasks: "200 任务/月", price: "按年订阅" },
    { name: "企业版", nodes: "不限", tasks: "不限", price: "定制报价" },
  ];
  tiers.forEach((t, i) => {
    const x = edgePad + i * 3.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 4.4, w: 2.85, h: 0.9, fill: { color: C.bgCard } });
    s.addText(t.name, { x: x + 0.1, y: 4.42, w: 2.65, h: 0.3, fontSize: 14, fontFace: FONT.header, color: C.cyan, bold: true, align: "center", margin: 0 });
    s.addText(`${t.nodes} · ${t.tasks} · ${t.price}`, { x: x + 0.1, y: 4.72, w: 2.65, h: 0.3, fontSize: 11, fontFace: FONT.body, color: C.gray, align: "center", margin: 0 });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 12 — 竞争壁垒
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("竞争壁垒", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.amber } });

  const barriers = [
    { n: "01", title: "信任可视化", desc: "业界首创「客户自验证」体系，将安全从厂商承诺变为客户可自行验证的事实。这是最大的差异化壁垒。" },
    { n: "02", title: "AI 原生集成", desc: "不是简单的 API 代理——脱敏引擎与 AI 推理深度集成，原始数据永不进入模型上下文。" },
    { n: "03", title: "通用平台", desc: "不绑定单一行业。供应链/金融/医疗/制造共用一套基础设施，网络效应随节点数指数增长。" },
    { n: "04", title: "价值闭环", desc: "不止于「安全传输」——量化每次协作的价值增量，让参与方看到 ROI，形成正反馈循环。" },
    { n: "05", title: "混合部署弹性", desc: "SaaS + 私有化灵活组合，满足从中小企业到军工级客户的全频谱需求。" },
  ];
  barriers.forEach((b, i) => {
    const x = edgePad + (i % 3) * 3.05;
    const y = 1.3 + Math.floor(i / 3) * 2.0;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.85, h: 1.8, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addText(b.n, { x: x + 0.12, y: y + 0.05, w: 0.5, h: 0.4, fontSize: 28, fontFace: FONT.header, color: C.amber, bold: true, margin: 0 });
    s.addText(b.title, { x: x + 0.6, y: y + 0.1, w: 2.1, h: 0.35, fontSize: 16, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(b.desc, { x: x + 0.12, y: y + 0.6, w: 2.6, h: 1.1, fontSize: 10, fontFace: FONT.body, color: C.gray, margin: 0, valign: "top" });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 13 — 路线图
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("产品路线图", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });

  const phases = [
    { phase: "V1.0 · 2026 Q3", title: "核心可用", items: ["节点管理 + 脱敏引擎", "基础分析脚本引擎", "管理控制台 + 审计", "3 节点 MVP 验证"], color: C.emerald },
    { phase: "V1.5 · 2026 Q4", title: "AI 集成", items: ["本地 LLM 推理支持", "AI 输出安全校验", "10+ 分析模板市场", "SaaS 协调节点上线"], color: C.cyan },
    { phase: "V2.0 · 2027 Q1", title: "规模化", items: ["100+ 节点支撑", "价值交换仪表盘", "行业解决方案包", "私有化企业版 GA"], color: C.amber },
  ];
  phases.forEach((p, i) => {
    const x = edgePad + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.4, w: 2.85, h: 3.5, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.4, w: 2.85, h: 0.04, fill: { color: p.color } });
    s.addText(p.phase, { x: x + 0.12, y: 1.55, w: 2.6, h: 0.3, fontSize: 10, fontFace: FONT.body, color: C.gray, margin: 0 });
    s.addText(p.title, { x: x + 0.12, y: 1.85, w: 2.6, h: 0.4, fontSize: 20, fontFace: FONT.header, color: p.color, bold: true, margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.12, y: 2.35, w: 1.0, h: 0.02, fill: { color: C.gray } });
    p.items.forEach((item, j) => {
      s.addText("▸ " + item, { x: x + 0.15, y: 2.6 + j * 0.45, w: 2.55, h: 0.4, fontSize: 12, fontFace: FONT.body, color: C.grayLt, margin: 0 });
    });
  });

  // timeline bar
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 5.1, w: 8.8, h: 0.04, fill: { color: C.gray } });
  s.addText("2026 Q3 ─────────────── 2026 Q4 ─────────────── 2027 Q1", { x: edgePad, y: 5.0, w: 8.8, h: 0.3, fontSize: 10, fontFace: FONT.body, color: C.gray, align: "center" });
})();

// ═══════════════════════════════════════════
// SLIDE 14 — 总结
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText("为什么选择通睿", { x: edgePad, y: 0.3, w: 8.8, h: 0.7, fontSize: 32, fontFace: FONT.header, color: C.white, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y: 1.05, w: 1.2, h: 0.04, fill: { color: C.cyan } });

  const reasons = [
    { title: "技术强制 > 承诺保证", desc: "沙箱网络隔离 + 输出白名单 + 暴露级别硬约束，代码说了算，不是合同说了算", color: C.cyan },
    { title: "安全可验证 > 安全可宣称", desc: "客户可以自己抓包看、自己验证日志，不用「相信我们」", color: C.emerald },
    { title: "协作有价值 > 协作有风险", desc: "不只是防泄露——量化每次协作的价值增量，让参与者看到 ROI", color: C.amber },
    { title: "通用平台 > 行业烟囱", desc: "一套基础设施覆盖供应链/金融/医疗/制造，网络效应随规模增长", color: "8B5CF6" },
  ];
  reasons.forEach((r, i) => {
    const y = 1.4 + i * 0.95;
    s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y, w: 8.8, h: 0.8, fill: { color: C.bgCard }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: edgePad, y, w: 0.06, h: 0.8, fill: { color: r.color } });
    s.addText(r.title, { x: edgePad + 0.2, y: y + 0.05, w: 4, h: 0.3, fontSize: 16, fontFace: FONT.header, color: C.white, bold: true, margin: 0 });
    s.addText(r.desc, { x: edgePad + 0.2, y: y + 0.4, w: 8.6, h: 0.3, fontSize: 12, fontFace: FONT.body, color: C.gray, margin: 0 });
  });
})();

// ═══════════════════════════════════════════
// SLIDE 15 — CLOSING
// ═══════════════════════════════════════════
(() => {
  const s = pres.addSlide();
  s.background = { color: "060E1E" };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.cyan } });
  s.addText("数据不出域，价值无边界", { x: 0.8, y: 1.6, w: 8.4, h: 1.0, fontSize: 36, fontFace: FONT.header, color: C.white, bold: true, align: "center" });
  s.addText("通睿 AI 安全网关", { x: 0.8, y: 2.7, w: 8.4, h: 0.6, fontSize: 22, fontFace: FONT.body, color: C.cyan, align: "center" });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.5, y: 3.5, w: 3.0, h: 0.03, fill: { color: C.gray } });
  s.addText("contact@tongrui.com  ·  www.tongrui.com", { x: 0.8, y: 3.7, w: 8.4, h: 0.4, fontSize: 14, fontFace: FONT.body, color: C.gray, align: "center" });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.3, w: 10, h: 0.06, fill: { color: C.gray } });
  s.addText("感谢关注", { x: 0.8, y: 4.6, w: 8.4, h: 0.4, fontSize: 12, fontFace: FONT.body, color: C.gray, align: "center" });
})();

// ── Output ──
pres.writeFile({ fileName: "/home/jipin/ai-security-gateway/ppt/通睿AI安全网关_投资人版.pptx" })
  .then(() => console.log("✓ Investor PPT generated"))
  .catch(e => console.error("✗", e));
