"""
Testes de regressão automatizados — Rodada Q5.

Reutiliza self_test.run_self_test_suite() para validar que os 4 cenários
canônicos continuam produzindo os resultados esperados.

Como rodar:
    cd scripts/
    python3 -m pytest ../tests/ -v

Ou (com pytest instalado globalmente):
    pytest tests/test_regression.py -v
"""

import sys
from pathlib import Path

# Adicionar scripts/ ao path para encontrar o módulo assessor
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest


def test_canonical_regression():
    """Os 4 cenários canônicos devem produzir resultados esperados.

    Falha se Conteúdo, Forma ou Sprint Badge divergirem dos valores gravados
    em CANONICAL_SCENARIOS (com margem ±0.2 em Conteúdo).
    """
    from assessor.self_test import run_self_test_suite
    rc = run_self_test_suite(verbose=True)
    assert rc == 0, "Pelo menos um cenário canônico falhou (regressão detectada)"


def test_individual_scenarios():
    """Roda cada cenário individualmente para diagnóstico granular."""
    from assessor.self_test import (
        CANONICAL_SCENARIOS,
        get_scenarios_dir,
        run_one_scenario,
    )
    scenarios_dir = get_scenarios_dir()

    failures = []
    for expected in CANONICAL_SCENARIOS:
        scenario_dir = scenarios_dir / expected.name
        assert scenario_dir.exists(), f"Diretório do cenário não encontrado: {scenario_dir}"
        ok, result = run_one_scenario(scenario_dir, expected, verbose=False)
        if not ok:
            failures.append((expected.name, result.get("problems", [])))

    if failures:
        msg = "Cenários com regressão:\n"
        for name, problems in failures:
            msg += f"  - {name}: {problems}\n"
        pytest.fail(msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
