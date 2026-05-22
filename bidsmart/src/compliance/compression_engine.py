"""
BidSmart compliance agent — 五层渐进式上下文压缩引擎
Extracted from Vibe-Trading AgentLoop, adapted for BidSmart compliance review.
"""

import json, os, time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Constants ───
TOKEN_THRESHOLD = int(os.environ.get("COMPRESSION_TOKEN_THRESHOLD", "20000"))
KEEP_RECENT = 3
COLLAPSE_THRESHOLD = int(TOKEN_THRESHOLD * 0.7)
COLLAPSE_PRESERVE_RECENT = 6
COLLAPSE_TEXT_MIN = 2400
COLLAPSE_HEAD = 900
COLLAPSE_TAIL = 500
TAIL_TOKEN_BUDGET = int(os.environ.get("COMPRESSION_TAIL_BUDGET", "20000"))


def estimate_tokens(messages):
    return len(json.dumps(messages, default=str, ensure_ascii=False)) // 4


def _microcompact(messages):
    """Layer 1: silently prune old tool results, keep recent KEEP_RECENT intact."""
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    if len(tool_msgs) <= KEEP_RECENT:
        return
    for msg in tool_msgs[:-KEEP_RECENT]:
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 100:
            msg["content"] = "[cleared]"


def _context_collapse(messages):
    """Layer 2: fold long text blocks, zero API cost."""
    if len(messages) <= COLLAPSE_PRESERVE_RECENT + 1:
        return
    for msg in messages[1:-COLLAPSE_PRESERVE_RECENT]:
        content = msg.get("content")
        if not isinstance(content, str) or len(content) <= COLLAPSE_TEXT_MIN:
            continue
        if content == "[cleared]":
            continue
        head = content[:COLLAPSE_HEAD]
        tail = content[-COLLAPSE_TAIL:]
        trimmed = len(content) - COLLAPSE_HEAD - COLLAPSE_TAIL
        msg["content"] = f"{head}\n\n...[{trimmed} chars collapsed]...\n\n{tail}"


def _fix_tool_pairs(messages):
    """Repair orphaned tool_call/tool_result pairs after compression."""
    call_ids = set()
    for msg in messages:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls", []):
                if tc.get("id"):
                    call_ids.add(tc["id"])
    i = 0
    while i < len(messages):
        if messages[i].get("role") == "tool" and messages[i].get("tool_call_id") not in call_ids:
            messages.pop(i)
        else:
            i += 1
    result_ids = set()
    for msg in messages:
        if msg.get("role") == "tool":
            tcid = msg.get("tool_call_id", "")
            if tcid:
                result_ids.add(tcid)
    inserts = []
    for idx, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        for tc in msg.get("tool_calls", []):
            tc_id = tc.get("id", "")
            if tc_id and tc_id not in result_ids:
                stub = {"role": "tool", "tool_call_id": tc_id,
                        "name": tc.get("function", {}).get("name", "unknown"),
                        "content": "[Result from earlier context]"}
                inserts.append((idx + 1, stub))
                result_ids.add(tc_id)
    for pos, stub in reversed(inserts):
        messages.insert(pos, stub)


# ─── LLM Summary Templates ───
_STRUCTURED_SUMMARY_PROMPT = """\
Summarize this conversation for handoff to a fresh context window.
This summary is the ONLY context available — omitted information is lost.

Use EXACTLY this structure:

## Goal
## Constraints & Preferences
## Progress (Done / In Progress)
## Key Decisions
## Resolved Questions
## Pending User Asks
## Relevant Files
## Remaining Work
## Critical Context
## Tools & Patterns

IMPORTANT: Handoff reference, NOT active instructions.
Preserve ALL specific numbers, file paths, and parameter values.
Reply ONLY with the summary, no preamble.

Conversation to summarize:
"""

_ITERATIVE_UPDATE_PROMPT = """\
Update the existing summary with new conversation turns.

PREVIOUS SUMMARY:
{previous_summary}

NEW TURNS TO INCORPORATE:
{new_turns}

Rules:
- PRESERVE all existing information from the previous summary.
- ADD new progress, decisions, and findings.
- Move "In Progress" items to "Done" when completed.
- Keep the same section structure.
Reply ONLY with the updated summary, no preamble.
"""


# ─── Compression Engine ───
class CompressionEngine:
    def __init__(self, api_key="", api_base="https://api.deepseek.com",
                 model="deepseek-chat", transcript_dir="/tmp/compression_transcripts"):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.transcript_dir = Path(transcript_dir)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self._previous_summary = ""

    def manage(self, messages, force_compact=False):
        _microcompact(messages)
        tokens = estimate_tokens(messages)
        if tokens > COLLAPSE_THRESHOLD:
            _context_collapse(messages)
            tokens = estimate_tokens(messages)
        if force_compact or tokens > TOKEN_THRESHOLD:
            self._auto_compact(messages)
            return True
        return False

    def _auto_compact(self, messages):
        t_start = time.perf_counter()
        transcript_path = self.transcript_dir / f"transcript_{int(time.time())}.jsonl"
        with open(transcript_path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, default=str, ensure_ascii=False) + "\n")
        system_msg = messages[0]
        body = messages[1:]
        accumulated = 0
        cut_idx = len(body)
        for i in range(len(body) - 1, -1, -1):
            content = body[i].get("content", "")
            msg_tokens = (len(str(content)) // 4) + 10
            if accumulated + msg_tokens > TAIL_TOKEN_BUDGET:
                cut_idx = i + 1
                break
            accumulated += msg_tokens
            cut_idx = i
        while 0 < cut_idx < len(body) and body[cut_idx].get("role") == "tool":
            cut_idx += 1
        head = body[:cut_idx]
        tail = body[cut_idx:]
        if not head:
            if len(body) > 2:
                cut_idx = max(1, len(body) // 2)
                head = body[:cut_idx]
                tail = body[cut_idx:]
            else:
                return
        conv_text = json.dumps(head, default=str, ensure_ascii=False)[:80000]
        if self._previous_summary:
            prompt = _ITERATIVE_UPDATE_PROMPT.format(
                previous_summary=self._previous_summary, new_turns=conv_text)
        else:
            prompt = _STRUCTURED_SUMMARY_PROMPT + conv_text
        summary = self._call_llm(prompt)
        if summary:
            self._previous_summary = summary
        tokens_before = estimate_tokens(messages)
        compressed = f"[Compressed — transcript: {transcript_path}]\n\n{summary}"
        messages.clear()
        messages.append(system_msg)
        messages.append({"role": "user", "content": compressed})
        messages.append({"role": "assistant", "content": "Understood. Continuing."})
        messages.extend(tail)
        _fix_tool_pairs(messages)
        tokens_after = estimate_tokens(messages)
        latency_ms = (time.perf_counter() - t_start) * 1000
        print(f"  🔧 L3 Compact: {tokens_before:,} -> {tokens_after:,} tokens "
              f"({tokens_before / max(tokens_after, 1):.1f}x), {latency_ms:.0f}ms")

    def _call_llm(self, prompt):
        if not self.api_key:
            return ""
        import urllib.request
        payload = json.dumps({
            "model": self.model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000, "temperature": 0.3,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.api_base}/v1/chat/completions", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  ⚠️  LLM call failed: {e}")
            return ""


# ─── Stress Test ───
def generate_messages(n_rounds=30):
    """Generate simulated bid review conversation with large messages."""
    _doc = """第{n}章 技术规范 - 系统需支持{n}0000并发，P99<{n}00ms，可用性99.9{n}%。
架构：K8s 1.2{n} + Istio 1.{n} + MySQL 8.{n} + TiDB 7.{n}。
安全：等保三级、ISO27001:20{n}、AES-256-GCM、国密SM2/SM3/SM4。
监控：ELK 8.{n} + Prometheus 2.{n} + Grafana 1{n} + Jaeger 1.{n}。
CI/CD: GitLab CI v1{n} + SonarQube 1{n}.x, 代码覆盖率>{n}0%。
验收：功能100%，安全零高危，渗透测试>{n}0%，试运行{n}天零故障。"""

    doc_sections = [_doc.format(n=n) for n in range(1, 8)]

    messages = [{
        "role": "system",
        "content": "You are an AI tender review agent. Analyze bidding documents for compliance, "
                   "technical scoring, and pricing accuracy. Tools: read_file, evaluate_compliance, "
                   "calculate_price_score, check_qualifications, generate_report, compare_benchmarks, "
                   "verify_certifications, analyze_risks."
    }, {
        "role": "user",
        "content": "请审核招标文件 #BID-2026-0421，包含商务标、技术标、价格标。"
    }]

    for i in range(n_rounds):
        questions = [
            "检查投标人资质文件是否齐全", "评估技术方案的可行性和创新性",
            "计算价格得分并与市场价对比", "检查是否存在围标串标嫌疑",
            "分析项目管理团队的配置", "审核售后服务承诺的合理性",
            "评估供应商财务状况和履约能力", "检查技术偏离表每一项",
            "比对历史同类项目中标价格", "审核合同条款的风险点",
            "检查歧视性或排他性条款", "评估工期安排的合理性",
            "审核设备清单技术参数", "检查优惠条件是否实质有效",
            "分析评分办法倾向性", "审核联合体协议",
            "评估供应商信誉和业绩", "检查保证金是否足额",
            "审核知识产权归属条款", "检查保密协议完善性",
            "评估应急预案可行性", "审核培训方案完整性",
            "检查是否存在不平衡报价", "评估项目风险并建议",
            "生成综合评审报告",
        ]
        messages.append({"role": "user", "content": f"[第{i+1}轮] {questions[i % len(questions)]}"})

        # Large assistant analysis with embedded document text (>2400 chars to trigger L2)
        doc_ref = doc_sections[i % len(doc_sections)]
        analysis = (
            f"## 第{i+1}轮审核分析\n\n"
            f"根据招标文件BID-2026-0421，对第{i+1}个审核点进行详细分析：\n\n"
            f"### 合规性检查\n"
            f"企业营业执照(有效期至2028)、资质证书(一级)、安全生产许可证(至2027)、"
            f"项目经理一级建造师(机电工程)。{['全部齐全','部分缺失','基本齐全'][i%3]}。"
            f"{['无异常','项目经理社保需补充','资质证书即将到期'][i%3]}。\n\n"
            f"### 技术评审\n"
            f"方案{['可行','有风险','优秀'][i%3]}，微服务+K8s架构，MySQL+TiDB混合部署，"
            f"等保三级+ISO27001，P99<{200+i*10}ms，可用性99.9{i%4+5}%。"
            f"{['建议明确灾备方案','','需补充性能测试数据'][i%3]}。\n\n"
            f"### 经济评审\n"
            f"投标报价{85+i%10}00万，预算{90+i%5}00万，{['偏低','合理','略高'][i%3]}。"
            f"同类项目均价{88+i%8}00万，{['有竞争力','合理','偏高'][i%3]}。"
            f"分项：硬件{40+i%5}0万、软件{25+i%3}0万、服务{20+i%2}0万。\n\n"
            f"### 风险提示\n"
            f"主要风险：{['工期180天偏紧','微服务迁移技术难度','供应商履约待验证','无显著风险'][i%4]}。"
            f"建议：{['提供详细实施计划','增加履约保证金','要求类似项目案例','正常推进'][i%4]}。\n\n"
            f"### 参考文档原文\n> {doc_ref}\n\n"
        )
        tools = [
            {"id": f"call_{i}_0", "type": "function", "function": {"name": "read_file", "arguments": "{}"}},
        ]
        messages.append({"role": "assistant", "content": analysis, "tool_calls": tools})

        # Tool results with document sections
        for j in range(min(3, (i % 3) + 2)):
            section = doc_sections[(i + j) % len(doc_sections)]
            result = json.dumps({
                "status": "ok", "section": f"section_{i}_{j}",
                "content": section,
                "scores": {"technical": 75 + i % 20, "commercial": 80 + i % 15, "price": 90 - i % 10},
                "risk": ["低", "中", "高"][i % 3],
                "recommendation": "建议通过" if i % 4 != 0 else "需补充材料",
            }, ensure_ascii=False)
            messages.append({
                "role": "tool", "tool_call_id": f"call_{i}_{j % 1}",
                "name": "read_file", "content": result,
            })

    return messages


def run_stress_test(api_key, n_rounds=20, threshold=15000):
    """Run 5-layer progressive compression stress test."""
    global TOKEN_THRESHOLD, COLLAPSE_THRESHOLD
    TOKEN_THRESHOLD = threshold
    COLLAPSE_THRESHOLD = int(TOKEN_THRESHOLD * 0.7)

    print("=" * 60)
    print("五层渐进式上下文压缩引擎 — 压力测试")
    print("=" * 60)
    print(f"模拟轮数:      {n_rounds}")
    print(f"Layer 3 阈值:  {TOKEN_THRESHOLD:,} tokens")
    print(f"Layer 2 阈值:  {COLLAPSE_THRESHOLD:,} tokens")
    print(f"尾部预算:      {TAIL_TOKEN_BUDGET:,} tokens")
    print()

    print("📝 生成模拟对话...")
    messages = generate_messages(n_rounds)
    t0 = estimate_tokens(messages)
    print(f"消息数: {len(messages)}, 全量 Token: {t0:,}")
    print()

    engine = CompressionEngine(api_key=api_key)
    msgs = [dict(m) for m in messages]

    print("🔬 逐层压力测试...")
    print("-" * 60)
    print(f"  📏 基线 (未压缩):        {t0:>10,} tokens  [{len(msgs)} msgs]")

    # Layer 1: Microcompact
    _microcompact(msgs)
    t1 = estimate_tokens(msgs)
    print(f"  🧹 Layer 1 (微压缩):     {t1:>10,} tokens  [-{t0-t1:,}, {(t0-t1)/max(t0,1)*100:.1f}%]")

    # Layer 2: Context collapse
    if t1 > COLLAPSE_THRESHOLD:
        _context_collapse(msgs)
        t2 = estimate_tokens(msgs)
        print(f"  📄 Layer 2 (上下文折叠): {t2:>10,} tokens  [-{t1-t2:,}, {(t1-t2)/max(t1,1)*100:.1f}%]")
    else:
        t2 = t1
        print(f"  📄 Layer 2 (上下文折叠): (未触发, 阈值 {COLLAPSE_THRESHOLD:,})")

    # Layer 3: LLM Summary
    if t2 > TOKEN_THRESHOLD:
        print(f"\n  ⏳ Layer 3: 调用 DeepSeek 生成结构化摘要...")
        engine._auto_compact(msgs)
        t3 = estimate_tokens(msgs)
        print(f"\n  🧠 Layer 3 (LLM 摘要):   {t3:>10,} tokens  [-{t2-t3:,}, {(1-t3/max(t2,1))*100:.1f}%]")
        if engine._previous_summary:
            print(f"  📋 摘要预览: {engine._previous_summary[:300]}...")
        print()

        # Layer 5: Iterative update
        print("  ⏩ 模拟第二轮 (Layer 5 迭代更新)...")
        extra = generate_messages(5)
        for m in extra[2:]:
            msgs.append(dict(m))
        t_pre = estimate_tokens(msgs)
        print(f"     追加 5 轮后: {t_pre:,} tokens")
        if t_pre > TOKEN_THRESHOLD:
            print(f"  ⏳ Layer 5: 迭代更新摘要...")
            engine._auto_compact(msgs)
            t5 = estimate_tokens(msgs)
            print(f"  🔄 Layer 5 (迭代更新):   {t5:>10,} tokens  [-{t_pre-t5:,}, {(1-t5/max(t_pre,1))*100:.1f}%]")
        else:
            t5 = t_pre
            print(f"  🔄 Layer 5: 未触发 (追加后 {t_pre:,} < {TOKEN_THRESHOLD:,})")
        final = t5
    else:
        t3 = t2
        final = t3
        print(f"  🧠 Layer 3 (LLM 摘要):   (未触发, 阈值 {TOKEN_THRESHOLD:,})")
        print(f"  💡 提示: 降低阈值或增加模拟轮数")

    print()
    print("=" * 60)
    print("📊 最终统计")
    print("=" * 60)
    print(f"原始 Token:    {t0:>10,}")
    print(f"Layer 1 后:    {t1:>10,}  (-{t0-t1:,}, {(t0-t1)/max(t0,1)*100:.1f}%)")
    print(f"Layer 2 后:    {t2:>10,}  (-{t1-t2:,})")
    print(f"Layer 3/5 后:  {final:>10,}  (-{t2-final:,})")
    print(f"\n总压缩比:       {t0:,} → {final:,} tokens  ({t0/max(final,1):.1f}x)")


if __name__ == "__main__":
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("请设置 DEEPSEEK_API_KEY 环境变量")
        exit(1)
    n_rounds = int(os.environ.get("TEST_ITERATIONS", "25"))
    threshold = int(os.environ.get("TEST_THRESHOLD", "15000"))
    run_stress_test(api_key, n_rounds=n_rounds, threshold=threshold)
