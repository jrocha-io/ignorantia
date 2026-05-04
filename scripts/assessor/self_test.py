"""
ignorantia.assessor.self_test — Bateria de regressão dos 4 cenários canônicos.

Roda os 4 cenários em test-cases/scenarios/ e compara contra valores esperados.
Falha se Conteúdo, Forma ou Sprint Badge divergirem.

Uso:
    python3 -m assessor.main --self-test
    # OU via pytest (importa run_self_test_suite e checa retorno 0)
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExpectedOutcome:
    """Valores esperados para um cenário canônico."""
    name: str
    version: str
    content_min: float  # nota mínima aceitável (margem ±0.2)
    content_max: float
    form_letter: str    # letra exata esperada
    badge_label_contains: str  # substring esperada na label_pt do badge

    def matches(self, content: float, form: str, badge_label: str) -> tuple[bool, list[str]]:
        """Retorna (ok, lista_de_problemas)."""
        problems = []
        if not (self.content_min <= content <= self.content_max):
            problems.append(
                f"Conteúdo {content:.2f} fora da faixa [{self.content_min}, {self.content_max}]"
            )
        if form != self.form_letter:
            problems.append(f"Forma '{form}' (esperado '{self.form_letter}')")
        if self.badge_label_contains.lower() not in badge_label.lower():
            problems.append(
                f"Sprint Badge label '{badge_label}' não contém '{self.badge_label_contains}'"
            )
        return (len(problems) == 0, problems)


# Os 4 cenários canônicos preservados em test-cases/scenarios/
# Margens absorvem variações pequenas legítimas de mudanças nos detectores;
# mudanças maiores indicam regressão real. As fixtures atuais correspondem
# ao estado v2.0.0-alpha24/alpha25 — Forma é sensível à completude do pacote
# (presença de README.md, ai-declaration.md, compliance-checklist.md, etc).
CANONICAL_SCENARIOS = [
    ExpectedOutcome(
        name="smoke",
        version="1.0.0",
        content_min=0.0, content_max=0.0,
        form_letter="E",
        badge_label_contains="NÃO-CLASSIFICÁVEL",
    ),
    ExpectedOutcome(
        name="corpus18",
        version="1.0.0",
        content_min=7.0, content_max=7.4,
        form_letter="A",
        badge_label_contains="B1",
    ),
    ExpectedOutcome(
        name="ghostwriter",
        version="0.1.0",
        content_min=3.5, content_max=3.9,
        form_letter="A",
        badge_label_contains="SUB-B4",
    ),
    ExpectedOutcome(
        name="casoH",
        version="1.0.0",
        content_min=6.1, content_max=6.5,
        form_letter="D",
        badge_label_contains="B3",
    ),
]


def get_scenarios_dir() -> Path:
    """Localiza test-cases/scenarios/ relativo ao módulo."""
    # Módulo está em scripts/assessor/ — repo root é parent.parent
    here = Path(__file__).parent.parent.parent
    sc = here / "test-cases" / "scenarios"
    if sc.exists():
        return sc
    # Fallback: procurar a partir do cwd
    cwd_sc = Path.cwd() / "test-cases" / "scenarios"
    if cwd_sc.exists():
        return cwd_sc
    raise FileNotFoundError(
        f"test-cases/scenarios/ não encontrado em {sc} nem {cwd_sc}"
    )


def run_one_scenario(scenario_dir: Path, expected: ExpectedOutcome,
                     verbose: bool = True) -> tuple[bool, dict]:
    """Roda o pipeline em um cenário e compara contra expected.

    Retorna (passou, dict_resultado).
    """
    out_path = Path("/tmp") / f"selftest_{expected.name}.json"

    cmd = [
        sys.executable, "-m", "assessor.main",
        "--package-dir", str(scenario_dir),
        "--content", str(scenario_dir / "content.json"),
        "--extraction", str(scenario_dir / "extraction.csv"),
        "--qa", str(scenario_dir / "quality-appraisal.csv"),
        "--searches", str(scenario_dir / "searches.json"),
        "--html", str(scenario_dir / "manuscript.html"),
        "--version", expected.version,
        "--topic-slug", expected.name,
        "--area-slug", "test",
        "--lang", "pt-BR",
        "--out", str(out_path),
    ]

    # cwd precisa ser scripts/ para o assessor.main resolver imports
    cwd = Path(__file__).parent.parent

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
    except subprocess.TimeoutExpired:
        return (False, {"error": "timeout"})

    if result.returncode != 0 or not out_path.exists():
        return (False, {"error": f"rc={result.returncode}", "stderr": result.stderr[-300:]})

    with open(out_path) as f:
        data = json.load(f)

    content = data["content_axis"]["score"]
    form = data["form_axis"]["letter"]
    badge_label = data.get("sprint_badge", {}).get("label_pt", "?")

    ok, problems = expected.matches(content, form, badge_label)

    if verbose:
        status_icon = "✅" if ok else "❌"
        print(f"  {status_icon} {expected.name}: Cont={content:.2f} Form={form} Badge={badge_label[:35]}")
        if problems:
            for p in problems:
                print(f"     ⚠️  {p}")

    return (ok, {
        "scenario": expected.name,
        "ok": ok,
        "content": content,
        "form": form,
        "badge_label": badge_label,
        "problems": problems,
    })


def run_self_test_suite(verbose: bool = True) -> int:
    """Roda os 4 cenários canônicos. Retorna 0 se todos passaram, 1 senão.

    Pode ser chamada via pytest ou via CLI.
    """
    scenarios_dir = get_scenarios_dir()
    if verbose:
        print("=" * 60)
        print("ignorantia self-test — bateria de regressão")
        print("=" * 60)
        print(f"Diretório: {scenarios_dir}")
        print()

    results = []
    for expected in CANONICAL_SCENARIOS:
        scenario_dir = scenarios_dir / expected.name
        if not scenario_dir.exists():
            if verbose:
                print(f"  ⚠️  {expected.name}: diretório não encontrado em {scenario_dir}")
            results.append({"scenario": expected.name, "ok": False,
                            "problems": [f"diretório não encontrado: {scenario_dir}"]})
            continue
        ok, res = run_one_scenario(scenario_dir, expected, verbose=verbose)
        results.append(res)

    if verbose:
        print()
        passed = sum(1 for r in results if r.get("ok"))
        total = len(results)
        print(f"{'='*60}")
        print(f"Resultado: {passed}/{total} cenários passaram")
        print(f"{'='*60}")

    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    sys.exit(run_self_test_suite())
