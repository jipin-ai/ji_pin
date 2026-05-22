"""Agent tools for BidSmart compliance review.

Tools follow Vibe-Trading pattern: ToolBase with JSON Schema parameters,
execute returns JSON strings. Used by AgentReviewLoop.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.skills import list_skills, load_skill as load_skill_from_disk


class ToolBase:
    """Base class for agent tools — inspired by Vibe-Trading ToolRegistry."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    repeatable: bool = False
    is_readonly: bool = True

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **kwargs) -> str:
        """Execute the tool. Returns JSON string."""
        raise NotImplementedError

    @classmethod
    def check_available(cls) -> bool:
        """Check if tool dependencies are met. Default: always available."""
        return True


# ── LoadSkillTool ──────────────────────────────────────────────────────


class LoadSkillTool(ToolBase):
    """Load a regulation SKILL.md by name, returning its full markdown content."""

    name = "load_skill"
    description = (
        "Load a regulation or guideline skill by name. "
        "Returns the full markdown content. "
        "Use this before reviewing any compliance item."
    )
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Skill name to load (e.g., '政府采购法', '招标投标法')",
            },
        },
        "required": ["name"],
    }

    async def execute(self, name: str = "") -> str:
        """Load skill by name or slug."""
        # Try by slug first, then by display name
        content = load_skill_from_disk(name)
        if content:
            return json.dumps({
                "status": "ok",
                "skill_name": name,
                "content": f"<skill name=\"{name}\">\n{content}\n</skill>",
            }, ensure_ascii=False)

        # Try matching by display name
        all_skills = list_skills()
        for s in all_skills:
            if s["name"] == name or s["slug"] == name:
                content = load_skill_from_disk(s["slug"])
                if content:
                    return json.dumps({
                        "status": "ok",
                        "skill_name": s["name"],
                        "content": f"<skill name=\"{s['name']}\">\n{content}\n</skill>",
                    }, ensure_ascii=False)

        # Not found
        available = [s["name"] for s in all_skills]
        return json.dumps({
            "status": "error",
            "error": f"Skill '{name}' not found. Available: {available}",
        }, ensure_ascii=False)


# ── ReadChunkTool ───────────────────────────────────────────────────────


class ReadChunkTool(ToolBase):
    """Read a specific chunk from the bid document by chunk index."""

    name = "read_chunk"
    description = (
        "Read a specific chunk of the bid document by chunk index. "
        "The document is split into ~2000-token chunks during upload. "
        "Use this to examine specific sections without loading the entire document."
    )
    parameters = {
        "type": "object",
        "properties": {
            "chunk_index": {
                "type": "integer",
                "description": "0-based chunk index to read",
            },
        },
        "required": ["chunk_index"],
    }
    is_readonly = True

    def __init__(self, chunks: List[Dict[str, Any]] | None = None):
        self._chunks: List[Dict[str, Any]] = chunks or []

    def set_chunks(self, chunks: List[Dict[str, Any]]):
        """Set the chunk list (called after document parsing)."""
        self._chunks = chunks

    async def execute(self, chunk_index: int = 0) -> str:
        if not self._chunks:
            return json.dumps({
                "status": "error",
                "error": "No document chunks loaded",
            }, ensure_ascii=False)

        if chunk_index < 0 or chunk_index >= len(self._chunks):
            return json.dumps({
                "status": "error",
                "error": f"Chunk index {chunk_index} out of range [0, {len(self._chunks)-1}]",
            }, ensure_ascii=False)

        chunk = self._chunks[chunk_index]
        return json.dumps({
            "status": "ok",
            "chunk_index": chunk_index,
            "total_chunks": len(self._chunks),
            "heading": chunk.get("heading", ""),
            "section_id": chunk.get("section_id", ""),
            "page_number": chunk.get("page_number", 0),
            "content": chunk["content"],
            "char_count": chunk.get("char_count", len(chunk["content"])),
        }, ensure_ascii=False)


# ── SearchKBTool ─────────────────────────────────────────────────────────


class SearchKBTool(ToolBase):
    """Semantic search in regulation knowledge base using BGE-M3 embeddings."""

    name = "search_kb"
    description = (
        "Search the regulation knowledge base for relevant legal provisions. "
        "Returns the top matching chunks with similarity scores. "
        "Use this to find applicable regulations before making compliance judgments."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (Chinese or English)",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 10)",
            },
        },
        "required": ["query"],
    }
    is_readonly = True

    def __init__(self, embedder=None):
        self._embedder = embedder

    def set_embedder(self, embedder):
        """Set the embedder instance (lazy init)."""
        self._embedder = embedder

    async def execute(self, query: str = "", top_k: int = 5) -> str:
        if not self._embedder:
            return json.dumps({
                "status": "error",
                "error": "Knowledge base embedder not initialized",
            }, ensure_ascii=False)

        top_k = min(max(top_k, 1), 10)

        try:
            results = await self._embedder.search(query, limit=top_k)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": f"Search failed: {e}",
            }, ensure_ascii=False)

        if not results:
            return json.dumps({
                "status": "ok",
                "query": query,
                "results": [],
                "message": "No matching regulations found",
            }, ensure_ascii=False)

        return json.dumps({
            "status": "ok",
            "query": query,
            "results": [
                {
                    "score": round(r.get("score", 0), 4),
                    "heading": r.get("heading", ""),
                    "content": r.get("content", "")[:2000],
                }
                for r in results[:top_k]
            ],
        }, ensure_ascii=False)


# ── SkillListTool ────────────────────────────────────────────────────────


class SkillListTool(ToolBase):
    """List all available skills."""

    name = "list_skills"
    description = "List all available regulation skills that can be loaded."
    parameters = {
        "type": "object",
        "properties": {},
    }
    is_readonly = True

    async def execute(self) -> str:
        skills = list_skills()
        return json.dumps({
            "status": "ok",
            "count": len(skills),
            "skills": [
                {"name": s["name"], "slug": s["slug"], "description": s["description"]}
                for s in skills
            ],
        }, ensure_ascii=False)
