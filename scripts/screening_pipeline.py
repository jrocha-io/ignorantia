#!/usr/bin/env python3
"""
screening_pipeline.py — Camada 2 do screening pipeline (DD-10).

Implementa a Fase 4 do PRISMA-2020 com decisões de inclusão/exclusão registradas
em granularidade adequada (por estágio, por reviewer, com timestamp). Cada estudo
passa por 3 estágios sequenciais:

1. **title screening** — decisão baseada apenas no título
2. **abstract screening** — decisão baseada no abstract (estudos que passaram título)
3. **full_text screening** — decisão baseada no full-text (estudos que passaram abstract)

A cada estágio, estudos são `kept` ou `discarded`, com reviewer e razão registrados.
A saída é `screening_log.csv` com schema PRISMA-compatible:

    study_id,doi,stage,decision,reason,reviewer,timestamp

A v2.17.0 introduz este módulo. Versões anteriores faziam screening implicitamente
durante extração de dados, sem separação explícita das três camadas. Reviewers Q1
agora têm o registro auditável que esperam (PRISMA-2020 item 8c).

Uso típico:

    from scripts.screening_pipeline import ScreeningPipeline
    sp = ScreeningPipeline(output_dir="search_results/")
    sp.load_studies("search_results/deduplicated_studies.json")
    # Decisão por estudo via human/AI reviewer
    sp.decide("S001", stage="title", decision="kept", reason="relevant", reviewer="human")
    sp.decide("S002", stage="title", decision="discarded", reason="off_topic", reviewer="human")
    # ...
    # Após screening, gera CSV + flow para PRISMA
    sp.export_csv()  # → screening_log.csv
    sp.export_prisma_counts()  # → screening_counts.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


Stage = Literal["title", "abstract", "full_text"]
Decision = Literal["kept", "discarded"]
ReviewerType = Literal["human", "ai_single", "ai_dual", "ai_assisted_human"]


@dataclass
class ScreeningEvent:
    """Decisão de screening atômica para um estudo em um estágio."""
    study_id: str
    doi: str | None
    stage: Stage
    decision: Decision
    reason: str
    reviewer: ReviewerType
    timestamp: str = field(default_factory=lambda:
                            datetime.now(timezone.utc).isoformat())

    def to_csv_row(self) -> list:
        return [self.study_id, self.doi or "", self.stage, self.decision,
                self.reason, self.reviewer, self.timestamp]


class ScreeningPipeline:
    """Pipeline de screening em 3 camadas (PRISMA-2020 Fase 4)."""

    CSV_HEADER = ["study_id", "doi", "stage", "decision", "reason",
                  "reviewer", "timestamp"]

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.events: list[ScreeningEvent] = []
        self.studies: dict[str, dict] = {}  # study_id -> metadata

    def load_studies(self, json_path: str | Path) -> int:
        """Carrega estudos deduplicados a partir de JSON. Retorna contagem."""
        path = Path(json_path)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        records = data if isinstance(data, list) else (
            data.get("results") or data.get("studies") or []
        )
        for i, rec in enumerate(records):
            study_id = (rec.get("study_id") or rec.get("id")
                        or f"S{i+1:04d}")
            self.studies[study_id] = rec
        return len(self.studies)

    def decide(self, study_id: str, stage: Stage, decision: Decision,
               reason: str, reviewer: ReviewerType = "human") -> None:
        """Registra decisão de screening para um estudo em um estágio."""
        if study_id not in self.studies:
            raise ValueError(f"study_id desconhecido: {study_id}")
        doi = self.studies[study_id].get("doi")
        ev = ScreeningEvent(
            study_id=study_id, doi=doi,
            stage=stage, decision=decision,
            reason=reason, reviewer=reviewer,
        )
        self.events.append(ev)

    def export_csv(self, path: str | Path | None = None) -> Path:
        """Exporta screening_log.csv (PRISMA-compatible)."""
        out_path = Path(path) if path else self.output_dir / "screening_log.csv"
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(self.CSV_HEADER)
            for ev in self.events:
                writer.writerow(ev.to_csv_row())
        return out_path

    def export_prisma_counts(self, path: str | Path | None = None) -> Path:
        """Exporta contagens compatíveis com PRISMA-2020 flow diagram."""
        out_path = Path(path) if path else self.output_dir / "screening_counts.json"

        def count(stage: Stage, decision: Decision) -> int:
            return sum(1 for e in self.events
                       if e.stage == stage and e.decision == decision)

        counts = {
            "total_loaded": len(self.studies),
            "title_kept": count("title", "kept"),
            "title_discarded": count("title", "discarded"),
            "abstract_kept": count("abstract", "kept"),
            "abstract_discarded": count("abstract", "discarded"),
            "full_text_kept": count("full_text", "kept"),
            "full_text_discarded": count("full_text", "discarded"),
            "discarded_reasons_by_stage": self._reasons_breakdown(),
        }
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(counts, fh, indent=2, ensure_ascii=False)
        return out_path

    def _reasons_breakdown(self) -> dict:
        """Conta razões de descarte por estágio."""
        breakdown: dict = {"title": {}, "abstract": {}, "full_text": {}}
        for ev in self.events:
            if ev.decision == "discarded":
                stage_dict = breakdown[ev.stage]
                stage_dict[ev.reason] = stage_dict.get(ev.reason, 0) + 1
        return breakdown

    def get_studies_in_stage(self, stage: Stage,
                              decision: Decision = "kept") -> list[str]:
        """Retorna study_ids que passaram (ou foram descartados) em um estágio."""
        return [e.study_id for e in self.events
                if e.stage == stage and e.decision == decision]


def _cli() -> int:
    p = argparse.ArgumentParser(
        description="Screening pipeline 3-stage (PRISMA-2020 Fase 4).")
    p.add_argument("--studies", required=True,
                   help="JSON com estudos deduplicados.")
    p.add_argument("--output-dir", default="search_results",
                   help="Diretório de saída (screening_log.csv + screening_counts.json).")
    p.add_argument("--demo", action="store_true",
                   help="Modo demo: aplica screening 'kept' a todos.")
    args = p.parse_args()

    sp = ScreeningPipeline(args.output_dir)
    n = sp.load_studies(args.studies)
    print(f"Carregados {n} estudos.")

    if args.demo:
        print("Modo demo: aplicando screening padrão.")
        for sid in sp.studies:
            sp.decide(sid, "title", "kept", "demo_relevant", "human")
            sp.decide(sid, "abstract", "kept", "demo_relevant", "human")
            sp.decide(sid, "full_text", "kept", "demo_relevant", "human")
        log_path = sp.export_csv()
        counts_path = sp.export_prisma_counts()
        print(f"  → {log_path}")
        print(f"  → {counts_path}")
        return 0

    print("Modo interativo não-implementado. Use --demo ou importe via API Python.")
    print("Schema esperado de chamada:")
    print("  sp.decide(study_id, stage='title|abstract|full_text', "
          "decision='kept|discarded', reason='...', reviewer='human|ai_*')")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
