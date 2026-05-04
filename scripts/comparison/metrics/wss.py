"""Métricas de SLR screening (categoria 2) — convenções de SYNERGY/CLEF eHealth TAR.

Definições canônicas (Cohen et al. 2006; Kanoulas et al. 2017-2019; van de Schoot 2025):

- **WSS@95** (Work Saved over Sampling at 95% recall):
    WSS@r = (TN + FN)/N - (1 - r) onde N=total docs e r=recall alvo (0.95).
    Mede economia de trabalho de triagem para atingir recall r.
    Range: ~0 (sem economia) a ~0.95 (economia máxima teórica).

- **recall@k%**: fração de relevantes encontrados após screening de k% do dataset.
- **ATD** (Average Time to Discover): número médio de iterações até encontrar cada relevante.
"""
from __future__ import annotations


def wss_at_recall(labels: list[int], rank_order: list[int], recall_target: float = 0.95) -> float:
    """Calcula WSS na taxa de recall alvo.

    Args:
        labels: lista [0/1] indicando relevância de cada documento (índices na ordem original).
        rank_order: indices de docs ordenados por probabilidade decrescente do classificador.
        recall_target: 0.95 (default canônico SYNERGY).

    Returns:
        WSS na recall alvo, no range [0, 1).
    """
    n = len(labels)
    if n == 0:
        return 0.0
    n_relevant = sum(labels)
    if n_relevant == 0:
        return 0.0
    target_relevant = int(round(recall_target * n_relevant))
    if target_relevant == 0:
        target_relevant = 1
    found = 0
    docs_screened = 0
    for idx in rank_order:
        docs_screened += 1
        if labels[idx] == 1:
            found += 1
            if found >= target_relevant:
                break
    # WSS = (N - docs_screened) / N - (1 - recall_target)
    return max(0.0, (n - docs_screened) / n - (1 - recall_target))


def recall_at_k_percent(labels: list[int], rank_order: list[int], k_percent: float = 10.0) -> float:
    """Recall após triar k% dos documentos."""
    n = len(labels)
    if n == 0:
        return 0.0
    n_relevant = sum(labels)
    if n_relevant == 0:
        return 0.0
    cutoff = max(1, int(n * k_percent / 100))
    found = sum(labels[idx] for idx in rank_order[:cutoff])
    return found / n_relevant


def atd(labels: list[int], rank_order: list[int]) -> float:
    """Average Time to Discover — média de posições de descoberta de relevantes."""
    n_relevant = sum(labels)
    if n_relevant == 0:
        return 0.0
    positions = []
    for pos, idx in enumerate(rank_order, start=1):
        if labels[idx] == 1:
            positions.append(pos)
    return sum(positions) / len(positions) if positions else 0.0
