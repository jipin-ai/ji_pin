"""Agent Review Loop — multi-turn compliance review with tools and compression.

Wraps the 5-layer compression engine from Vibe-Trading architecture.
Each iteration: L1 microcompact → LLM stream_chat → tool execution → L3 on threshold.
"""

from __future__ import annotations

import json
import logging
import time as _time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from openai import AsyncOpenAI

from src.compliance.compression_engine import (
    CompressionEngine,
    estimate_tokens,
    COLLAPSE_THRESHOLD,
    TOKEN_THRESHOLD,
)
from src.compliance.agent_tools import (
    LoadSkillTool,
    ReadChunkTool,
    SearchKBTool,
    SkillListTool,
)

logger = logging.getLogger(__name__)

# ── System Prompt ────────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """你是标书智审(BidSmart)的AI合规审查Agent。你可以调用工具来加载法规知识、读取标书分块、搜索知识库。

## 审查规则
1. 在做出合规判定前，必须先 load_skill 加载相关法规
2. 需要标书具体内容时，使用 read_chunk 读取对应分块
3. 不确定适用法规时，使用 search_kb 搜索
4. 逐项比对招标要求与投标响应，判定 compliant/partial/non_compliant/unable_to_judge
5. 每项判定必须引用具体法规条款

## 可用的法规技能
使用 list_skills 查看当前可加载的法规列表。

## 回答格式
审查完成后，输出JSON格式的审查结果。"""


# ── Session Store ────────────────────────────────────────────────────────

_sessions: Dict[str, Dict[str, Any]] = {}


def _get_or_create_session(
    session_id: str | None,
) -> tuple[str, Dict[str, Any]]:
    """Get existing session or create a new one."""
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    new_id = session_id or f"agent-{uuid.uuid4().hex[:8]}"
    _sessions[new_id] = {
        "id": new_id,
        "messages": [],
        "iteration_count": 0,
        "compression_stats": {
            "l1_applied": 0,
            "l2_applied": 0,
            "l3_applied": 0,
            "l5_applied": 0,
            "peak_tokens": 0,
        },
    }
    return new_id, _sessions[new_id]


# ── AgentReviewLoop ──────────────────────────────────────────────────────


class AgentReviewLoop:
    """Multi-turn compliance review agent with compression.

    Uses the 5-layer compression engine to manage context in long
    review sessions, especially with large bid documents.
    """

    def __init__(
        self,
        settings,
        chunks: List[Dict[str, Any]] | None = None,
        max_iterations: int = 30,
    ):
        self.settings = settings
        self.max_iterations = max_iterations

        # LLM client
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key or "***",
            base_url=settings.deepseek_base_url or "https://api.deepseek.com",
        )

        # Compression engine
        self.compression = CompressionEngine(
            api_key=settings.deepseek_api_key or "",
            api_base=getattr(settings, "deepseek_base_url", "https://api.deepseek.com"),
            model=getattr(settings, "deepseek_model", "deepseek-chat"),
            transcript_dir=str(Path(getattr(settings, "storage_root", "./storage")) / "transcripts"),
        )

        # Tools
        self.load_skill_tool = LoadSkillTool()
        self.read_chunk_tool = ReadChunkTool(chunks or [])
        self.search_kb_tool = SearchKBTool()
        self.skill_list_tool = SkillListTool()

        self._tools = [
            self.load_skill_tool,
            self.read_chunk_tool,
            self.search_kb_tool,
            self.skill_list_tool,
        ]

    def set_embedder(self, embedder):
        """Set knowledge base embedder for search tool."""
        self.search_kb_tool.set_embedder(embedder)

    def set_chunks(self, chunks: List[Dict[str, Any]]):
        """Set document chunks for read tool."""
        self.read_chunk_tool.set_chunks(chunks)

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI function-calling definitions for all tools."""
        return [t.to_openai_schema() for t in self._tools]

    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Execute a tool by name and return its JSON result."""
        for tool in self._tools:
            if tool.name == name:
                try:
                    return await tool.execute(**args)
                except Exception as e:
                    return json.dumps({
                        "status": "error",
                        "tool": name,
                        "error": str(e),
                    }, ensure_ascii=False)

        return json.dumps({
            "status": "error",
            "error": f"Tool '{name}' not found",
        }, ensure_ascii=False)

    def _build_system_message(self) -> Dict[str, str]:
        """Build the system prompt with available skills."""
        from src.skills import list_skills as _ls
        skills = _ls()
        skill_names = ", ".join(s["name"] for s in skills)
        return {
            "role": "system",
            "content": AGENT_SYSTEM_PROMPT.replace(
                "使用 list_skills 查看当前可加载的法规列表。",
                f"当前可用的法规技能: {skill_names}。使用 load_skill 加载具体法规。"
            ),
        }

    async def run(
        self,
        user_message: str,
        session_id: str | None = None,
        history: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """Run the agent review loop.

        Args:
            user_message: User's review request.
            session_id: Optional session ID for continuing a session.
            history: Optional prior conversation messages.

        Returns:
            Dict with content, tool_calls, iterations, session_id, compression_stats.
        """
        sid, session = _get_or_create_session(session_id)

        # Build messages
        if not session["messages"]:
            session["messages"].append(self._build_system_message())
            if history:
                session["messages"].extend(history)

        session["messages"].append({"role": "user", "content": user_message})

        iteration = 0
        final_content = ""
        all_tool_calls: List[Dict[str, Any]] = []

        try:
            while iteration < self.max_iterations:
                iteration += 1
                session["iteration_count"] += 1

                # ── Layer 1: Microcompact (every iteration, zero cost) ──
                self.compression.manage(session["messages"])
                tokens = estimate_tokens(session["messages"])
                session["compression_stats"]["peak_tokens"] = max(
                    session["compression_stats"]["peak_tokens"], tokens
                )
                session["compression_stats"]["l1_applied"] += 1

                logger.debug(f"Iteration {iteration}: {tokens} tokens")

                # ── LLM Stream Chat ──
                response = await self.client.chat.completions.create(
                    model=getattr(self.settings, "deepseek_model", "deepseek-chat"),
                    messages=session["messages"],
                    tools=self._get_tool_definitions(),
                    temperature=0.1,
                    max_tokens=4000,
                )

                choice = response.choices[0]
                msg = choice.message

                # ── No tool calls → final answer ──
                if not msg.tool_calls:
                    final_content = msg.content or ""
                    assistant_msg = {"role": "assistant", "content": final_content}
                    session["messages"].append(assistant_msg)
                    break

                # ── Has tool calls → append assistant first, then execute and append results ──
                # OpenAI requires: assistant(tool_calls) → tool results → next turn
                session["messages"].append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                # Now execute tools and append results
                tool_calls_data = []
                for tc in msg.tool_calls:
                    func = tc.function
                    args = json.loads(func.arguments) if func.arguments else {}
                    result = await self._execute_tool(func.name, args)

                    tool_calls_data.append({
                        "tool": func.name,
                        "args": args,
                        "result_preview": result[:200],
                    })
                    all_tool_calls.append(tool_calls_data[-1])

                    session["messages"].append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func.name,
                        "content": result,
                    })

        except Exception as exc:
            logger.exception(f"AgentLoop error: {exc}")
            return {
                "content": f"审查过程出错: {exc}",
                "tool_calls": all_tool_calls,
                "iterations": iteration,
                "session_id": sid,
                "compression_stats": session["compression_stats"],
                "error": str(exc),
            }

        return {
            "content": final_content or "审查完成，但未生成最终结论。",
            "tool_calls": all_tool_calls,
            "iterations": iteration,
            "session_id": sid,
            "compression_stats": session["compression_stats"],
        }

    async def continue_session(
        self,
        session_id: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """Continue an existing review session."""
        return await self.run(user_message, session_id=session_id)
