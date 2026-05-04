"""Métricas de ranking para venue recommenders (categoria 1).

Implementação puramente Python — sem numpy. Todas as funções aceitam:
  ranking: lista ordenada (rank 1 primeiro) de venue_id strings
  ground_truth_id: venue_id correto (publicação real)

Métricas:
- topk_match(ranking, gt, k): bool
- mrr(ranking, gt): 1/rank se presente, 0 caso contrário
- ndcg_at_k(ranking, gt, k): nDCG@k para relevância binária (gt=1, demais=0)
"""
from __future__ import annotations

import math


def topk_match(ranking: list[str], ground_truth_id: str, k: int = 5) -> bool:
    """Retorna True se ground_truth_id está nos top-k posições de ranking."""
    return ground_truth_id in ranking[:k]


def mrr(ranking: list[str], ground_truth_id: str) -> float:
    """Reciprocal rank: 1/rank se ground_truth_id presente, 0 caso contrário.

    Note: para batches, MRR final = média de mrr individuais.
    """
    try:
        idx = ranking.index(ground_truth_id)
        return 1.0 / (idx + 1)
    except ValueError:
        return 0.0


def ndcg_at_k(ranking: list[str], ground_truth_id: str, k: int = 10) -> float:
    """nDCG@k para relevância binária — gt=1, todos os demais=0.

    DCG = sum_{i=1}^k (rel_i / log2(i+1))
    IDCG = 1 / log2(2) = 1.0 (apenas um item relevante, posição 1)
    nDCG = DCG / IDCG = DCG (por construção, com 1 item relevante).
    """
    if not ground_truth_id:
        return 0.0
    dcg = 0.0
    for i, item in enumerate(ranking[:k], start=1):
        rel = 1.0 if item == ground_truth_id else 0.0
        if rel:
            dcg += rel / math.log2(i + 1)
    return dcg  # IDCG=1.0 para relevância binária com 1 hit


def aggregate_topk(rankings: list[list[str]], ground_truths: list[str], k: int) -> float:
    """Top-k accuracy agregado: % de rankings onde gt está em top-k."""
    if not rankings:
        return 0.0
    hits = sum(1 for r, gt in zip(rankings, ground_truths) if topk_match(r, gt, k))
    return hits / len(rankings)


def aggregate_mrr(rankings: list[list[str]], ground_truths: list[str]) -> float:
    """MRR médio sobre batch."""
    if not rankings:
        return 0.0
    return sum(mrr(r, gt) for r, gt in zip(rankings, ground_truths)) / len(rankings)


def aggregate_ndcg(rankings: list[list[str]], ground_truths: list[str], k: int = 10) -> float:
    """nDCG@k médio sobre batch."""
    if not rankings:
        return 0.0
    return sum(ndcg_at_k(r, gt, k) for r, gt in zip(rankings, ground_truths)) / len(rankings)
