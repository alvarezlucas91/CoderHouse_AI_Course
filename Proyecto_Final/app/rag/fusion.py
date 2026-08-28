from collections.abc import Sequence

from app.schemas import Evidence


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Evidence]],
    *,
    limit: int,
    rank_constant: int = 60,
) -> list[Evidence]:
    """Fuse rankings by stable evidence ID and preserve provider scores."""
    if limit < 1:
        raise ValueError("limit must be positive")
    if rank_constant < 1:
        raise ValueError("rank_constant must be positive")

    fused_scores: dict[str, float] = {}
    evidence_by_id: dict[str, Evidence] = {}
    for ranking in rankings:
        seen_in_ranking: set[str] = set()
        for rank, item in enumerate(ranking, start=1):
            if item.evidence_id in seen_in_ranking:
                continue
            seen_in_ranking.add(item.evidence_id)
            evidence_by_id.setdefault(item.evidence_id, item)
            fused_scores[item.evidence_id] = (
                fused_scores.get(item.evidence_id, 0.0) + 1.0 / (rank_constant + rank)
            )

    ordered_ids = sorted(fused_scores, key=lambda key: (-fused_scores[key], key))[:limit]
    return [
        evidence_by_id[evidence_id].model_copy(
            update={"fused_score": fused_scores[evidence_id]}
        )
        for evidence_id in ordered_ids
    ]

