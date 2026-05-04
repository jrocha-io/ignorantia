"""Métricas de compliance checking (categoria 3) — F1 item-level e Cohen's κ.

Convenção: cada item da reporting guideline (PRISMA-2020 tem 27) é avaliado como
True/False por anotador humano e por ferramenta automatizada (ignorantia ou Penelope/etc.).

Métricas:
- F1 item-level (precision, recall, F1)
- Sensibilidade (TPR) e especificidade (TNR)
- Cohen's κ (concordância além do acaso)
"""
from __future__ import annotations


def confusion_matrix(human: list[bool], tool: list[bool]) -> tuple[int, int, int, int]:
    """Retorna (TP, TN, FP, FN) — convenção: human=True é positivo (item compliant)."""
    if len(human) != len(tool):
        raise ValueError(f"length mismatch: human={len(human)} tool={len(tool)}")
    tp = sum(1 for h, t in zip(human, tool) if h and t)
    tn = sum(1 for h, t in zip(human, tool) if not h and not t)
    fp = sum(1 for h, t in zip(human, tool) if not h and t)
    fn = sum(1 for h, t in zip(human, tool) if h and not t)
    return tp, tn, fp, fn


def precision(tp: int, fp: int) -> float:
    return tp / (tp + fp) if (tp + fp) > 0 else 0.0


def recall(tp: int, fn: int) -> float:
    return tp / (tp + fn) if (tp + fn) > 0 else 0.0


def f1_score(tp: int, fp: int, fn: int) -> float:
    p = precision(tp, fp)
    r = recall(tp, fn)
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def sensitivity(tp: int, fn: int) -> float:
    """Taxa de verdadeiros positivos (= recall)."""
    return recall(tp, fn)


def specificity(tn: int, fp: int) -> float:
    """Taxa de verdadeiros negativos."""
    return tn / (tn + fp) if (tn + fp) > 0 else 0.0


def cohen_kappa(human: list[bool], tool: list[bool]) -> float:
    """Cohen's κ — concordância além do acaso.

    κ = (po - pe) / (1 - pe)
    onde po = concordância observada, pe = concordância esperada por acaso.
    Range: -1 (discordância total) a 1 (concordância total). 0 = acaso.
    """
    n = len(human)
    if n == 0 or len(tool) != n:
        return 0.0
    tp, tn, fp, fn = confusion_matrix(human, tool)
    po = (tp + tn) / n
    p_human_pos = (tp + fn) / n
    p_tool_pos = (tp + fp) / n
    pe = p_human_pos * p_tool_pos + (1 - p_human_pos) * (1 - p_tool_pos)
    return (po - pe) / (1 - pe) if (1 - pe) > 0 else 0.0


def evaluate_compliance(human_annotation: dict[str, bool],
                        tool_annotation: dict[str, bool]) -> dict[str, float]:
    """Avalia ferramenta contra anotação humana, item-a-item.

    Args:
        human_annotation: {item_id: compliant_bool}
        tool_annotation:  {item_id: compliant_bool}

    Returns:
        dict com precision, recall, f1, sensitivity, specificity, kappa, support.
    """
    common_items = sorted(set(human_annotation) & set(tool_annotation))
    if not common_items:
        return {"error": "no common items between human and tool annotations"}
    h = [bool(human_annotation[k]) for k in common_items]
    t = [bool(tool_annotation[k]) for k in common_items]
    tp, tn, fp, fn = confusion_matrix(h, t)
    return {
        "support": len(common_items),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": precision(tp, fp),
        "recall": recall(tp, fn),
        "f1": f1_score(tp, fp, fn),
        "sensitivity": sensitivity(tp, fn),
        "specificity": specificity(tn, fp),
        "kappa": cohen_kappa(h, t),
    }
