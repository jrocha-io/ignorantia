"""
ignorantia v2.0 — Compliance Engine

Engine determinístico de avaliação de aderência a requisitos formais de venues.

Pipeline em 7 estágios:
  Stage 1: Parse & Normalize  (parse.py)
  Stage 2: Hard Requirements  (hard_rules.py)
  Stage 3: Reporting Guidelines  (guidelines.py)
  Stage 4: Scope Matching  (scope.py)
  Stage 5: Aggregation  (aggregator.py)
  Stage 6: Gap Prioritization  (gaps.py)
  Stage 7: Multi-Venue Ranking  (ranking.py)

Sem treinamento de modelos. Todas as componentes são auditáveis.
"""

__version__ = "2.0.0"

from .engine import VenueComplianceEngine, ComplianceReport

__all__ = ["VenueComplianceEngine", "ComplianceReport"]
