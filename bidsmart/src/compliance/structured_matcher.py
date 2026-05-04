"""Stage 0: Structured alignment — section numbering hierarchy extraction and mapping.

Based on Legal-DC clause-boundary segmentation and Adaptive HR Tree Reasoning.
Extracts numbered section hierarchies from both tender and bid documents,
then maps requirements to bid sections via structural alignment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SectionNode:
    """A node in the section numbering tree."""
    number: str          # "3.1.2"
    heading: str         # section heading text
    level: int           # depth (1=chapter, 2=section, 3=subsection)
    page: int            # page number
    children: list[SectionNode] = field(default_factory=list)


def extract_numbering_tree(sections: list, doc_type: str = "tender") -> list[SectionNode]:
    """Build a section numbering tree from parsed document sections.

    Detects numbering patterns: 3.1, 3.1.2, 一、, 第X章, (一), etc.
    Returns flat list of leaf nodes with full number paths.
    """
    nodes: list[SectionNode] = []

    for sec in sections:
        heading = sec.heading or ""
        level = sec.level or 0
        page = sec.page_number or 0

        # Try to extract section number from heading
        number = _extract_section_number(heading)
        if not number and level > 0:
            number = f"s{sec.section_id or ''}"

        if number:
            nodes.append(SectionNode(
                number=number,
                heading=heading,
                level=level,
                page=page,
            ))

    return nodes


def _extract_section_number(text: str) -> str:
    """Extract section number from heading text.
    
    Examples: "3.1.2 技术要求" → "3.1.2", "一、项目概况" → "一"
    """
    patterns = [
        r'^(\d+(?:\.\d+)*)\s',           # 3.1.2
        r'^第([一二三四五六七八九十\d]+)章',  # 第X章
        r'^第([一二三四五六七八九十\d]+)节',  # 第X节
        r'^([一二三四五六七八九十]+)[、．]',   # 一、
        r'^（([一二三四五六七八九十]+)）',      # （一）
        r'^(\d+)[、．)]\s',              # 1、
        r'^\((\d+)\)\s',                 # (1)
    ]
    for pat in patterns:
        m = re.match(pat, text)
        if m:
            return m.group(1)
    return ""


def align_requirements(
    requirements: list,
    tender_nodes: list[SectionNode],
    bid_nodes: list[SectionNode],
) -> dict[str, tuple[str, float]]:
    """Align requirements to bid sections via section numbering.

    For each extracted requirement, find its section number in the tender,
    then look for the same or nearest section number in the bid document.

    Returns: {requirement_id: (bid_section_heading, alignment_score)}
    """
    alignment: dict[str, tuple[str, float]] = {}

    # Build tender number → section map
    tender_map: dict[str, SectionNode] = {}
    for node in tender_nodes:
        tender_map[node.number] = node

    # Build bid number → section map
    bid_map: dict[str, SectionNode] = {}
    for node in bid_nodes:
        bid_map[node.number] = node

    for req in requirements:
        req_id = req.id
        # Try to find section number from requirement heading
        req_number = ""
        if req.section_heading:
            req_number = _extract_section_number(req.section_heading)

        if req_number and req_number in bid_map:
            # Exact match
            alignment[req_id] = (bid_map[req_number].heading, 1.0)
        elif req_number:
            # Partial match: find closest number
            best_score = 0.0
            best_heading = ""
            for bid_num, bid_node in bid_map.items():
                score = _number_similarity(req_number, bid_num)
                if score > best_score:
                    best_score = score
                    best_heading = bid_node.heading
            if best_score > 0.3:
                alignment[req_id] = (best_heading, best_score)

    return alignment


def _number_similarity(a: str, b: str) -> float:
    """Calculate section number similarity.
    
    "3.1.2" vs "3.1" = 0.67 (2/3 levels match)
    "3.1" vs "3.2" = 0.5 (first level matches)
    """
    if a == b:
        return 1.0
    a_parts = a.replace('.', ' ').split()
    b_parts = b.replace('.', ' ').split()
    if not a_parts or not b_parts:
        return 0.0
    matches = sum(1 for ap, bp in zip(a_parts, b_parts) if ap == bp)
    max_len = max(len(a_parts), len(b_parts))
    return matches / max_len
