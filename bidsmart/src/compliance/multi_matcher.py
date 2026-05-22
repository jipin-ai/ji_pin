"""Stage 1: Multi-strategy matching fusion.

Based on Adaptive Hybrid Retrieval (2604.14222) and vstash (2604.15484).
Combines three independent matching strategies and fuses results via weighted scoring.

Paths:
  A: Structured alignment (section number mapping)
  B: Semantic matching (BGE embedding cosine similarity)
  C: Keyword matching (BM25 / exact keyword overlap)
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


@dataclass
class MatchResult:
    """Result from a single matching strategy."""
    path: str                         # "structured" | "semantic" | "keyword"
    bid_heading: str
    bid_text: str
    bid_page: int
    score: float                      # 0-1
    rank: int                         # 1 = best


@dataclass
class FusedMatch:
    """Fused match result from all strategies."""
    bid_heading: str
    bid_text: str
    bid_page: int
    agreement_score: float            # 0-1, how well strategies agree
    path_votes: dict[str, float]      # per-path scores
    consensus: str                    # "high" (≥2 agree) | "medium" | "low"


def fuse_matches(
    structured_matches: list[MatchResult],
    semantic_matches: list[MatchResult],
    keyword_matches: list[MatchResult],
    weights: dict[str, float] | None = None,
) -> FusedMatch | None:
    """Fuse results from three matching strategies.

    Weighted by strategy reliability:
    - Structured alignment is most reliable for well-numbered docs
    - Semantic matching handles differently-phrased sections
    - Keyword matching catches exact term matches

    Returns None if no strategy found a match above threshold.
    """
    if weights is None:
        weights = {"structured": 0.4, "semantic": 0.35, "keyword": 0.25}

    all_matches = structured_matches + semantic_matches + keyword_matches
    if not all_matches:
        return None

    # Group by bid heading (normalize for comparison)
    heading_groups: dict[str, list[MatchResult]] = {}
    for m in all_matches:
        key = m.bid_heading[:80] if m.bid_heading else m.bid_text[:80]
        if key not in heading_groups:
            heading_groups[key] = []
        heading_groups[key].append(m)

    # Find the best group (highest weighted average score)
    best_group = None
    best_weighted_score = 0.0

    for key, matches in heading_groups.items():
        path_scores: dict[str, list[float]] = {}
        for m in matches:
            if m.path not in path_scores:
                path_scores[m.path] = []
            path_scores[m.path].append(m.score)

        # Weighted average: each path contributes its best score × weight
        weighted = 0.0
        total_weight = 0.0
        for path, w in weights.items():
            if path in path_scores:
                weighted += max(path_scores[path]) * w
                total_weight += w

        if total_weight > 0:
            avg_score = weighted / total_weight
            if avg_score > best_weighted_score:
                best_weighted_score = avg_score
                best_group = (key, matches, path_scores)

    if not best_group:
        return None

    key, matches, path_scores = best_group

    # Compute agreement score: how many paths point to same heading?
    paths_voting = len(path_scores)
    agreement = paths_voting / 3.0  # 3 strategies total

    # Boost: if structured and semantic agree, high confidence
    if "structured" in path_scores and "semantic" in path_scores:
        agreement = min(1.0, agreement + 0.15)

    # Determine consensus level
    if paths_voting >= 2:
        consensus = "high"
    elif paths_voting == 1 and best_weighted_score > 0.5:
        consensus = "medium"
    else:
        consensus = "low"

    # Pick the best match's text
    best_match = max(matches, key=lambda m: m.score * weights.get(m.path, 0.3))

    # Build per-path vote summary
    path_votes = {}
    for path, scores in path_scores.items():
        path_votes[path] = round(max(scores), 3)

    return FusedMatch(
        bid_heading=best_match.bid_heading,
        bid_text=best_match.bid_text,
        bid_page=best_match.bid_page,
        agreement_score=round(best_weighted_score, 4),
        path_votes=path_votes,
        consensus=consensus,
    )


def compute_bm25_score(
    query_keywords: list[str],
    document: str,
    all_documents: list[str],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Compute simplified BM25 score for keyword matching.

    BM25(query, doc) = Σ IDF(qi) * (tf(qi,doc) * (k1+1)) / (tf(qi,doc) + k1*(1-b+b*|doc|/avgdl))

    This is an approximation — full BM25 would require term frequency indexing.
    For our use case (small section count per document), direct computation is fine.
    """
    if not query_keywords or not document:
        return 0.0

    # Average document length
    doc_lengths = [len(d) for d in all_documents]
    avgdl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0
    doc_len = len(document)
    N = len(all_documents)

    score = 0.0
    for kw in query_keywords:
        # Term frequency in document
        tf = document.count(kw)
        if tf == 0:
            continue

        # Document frequency (how many docs contain this kw)
        df = sum(1 for d in all_documents if kw in d)
        if df == 0:
            continue

        # IDF
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

        # BM25 term score
        numerator = tf * (k1 + 1.0)
        denominator = tf + k1 * (1.0 - b + b * doc_len / avgdl)
        score += idf * numerator / denominator

    # Normalize to 0-1 (heuristic: cap at ~10 for reasonable keyword overlap)
    return min(1.0, score / 10.0)
