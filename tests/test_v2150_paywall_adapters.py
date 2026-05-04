"""Smoke tests v2.15.0 — adapters paywall com cascata KEY→PROXY→FALLBACK_MD.

Cobre:
- 16 adapters paywall (R2-R6 das rodadas v2.12-v2.16): Elsevier x3, Springer/Wiley/IEEE/WoS,
  APA/CINAHL/JSTOR/Sage, ACM/SSRN/Hein/ProQuest, Google Scholar
- Cascata: modo MOCK + modo FALLBACK_MD (sem credencial)
- Integração ao orquestrador: TIER1_RUNNERS, TIER_DATABASES tier2_paywall, disclosure
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


def _run_mock(adapter: str, tmp_path) -> dict:
    out = tmp_path / f"{adapter}.json"
    cmd = [sys.executable, str(ROOT / f"scripts/searches/{adapter}.py"),
           "--query", "test", "--mock", "--output", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert res.returncode == 0, f"{adapter} --mock falhou: {res.stderr}"
    return json.loads(out.read_text(encoding="utf-8"))


def _run_fallback(adapter: str, tmp_path) -> dict:
    """Roda sem chave + sem proxy → deve gerar fallback .md."""
    out = tmp_path / f"{adapter}.json"
    cmd = [sys.executable, str(ROOT / f"scripts/searches/{adapter}.py"),
           "--query", "test", "--output", str(out),
           "--output-dir", str(tmp_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    # Pode retornar 0 (FALLBACK_MD bem-sucedido) ou 1 (erro KEY/PROXY)
    return json.loads(out.read_text(encoding="utf-8"))


# ============ Template _adapter_base ============

def test_adapter_base_imports():
    """Template arquitetural pode ser importado."""
    from _adapter_base import (PaywallAdapter, AdapterResult, FetchedItem,
                                LocalFilter, make_cli)
    assert PaywallAdapter is not None
    assert AdapterResult is not None


def test_adapter_base_local_filter_filters_correctly():
    """LocalFilter descarta por janela temporal e idioma."""
    from _adapter_base import FetchedItem, LocalFilter
    items = [
        FetchedItem(title="A", year=2020, language="en"),
        FetchedItem(title="B", year=2018, language="en"),  # fora da janela
        FetchedItem(title="C", year=2021, language="ja"),  # idioma rejeitado
        FetchedItem(title="D", year=2022, language="en"),
    ]
    lf = LocalFilter(year_start=2019, year_end=2023, accepted_languages=["en", "pt"])
    kept = lf.apply(items)
    assert len(kept) == 2  # A e D
    assert lf.discarded_reasons == {
        "out_of_temporal_window": 1,
        "language_not_accepted": 1,
    }


# ============ R2 — Elsevier (3 adapters) ============

def test_scopus_full_mock(tmp_path):
    d = _run_mock("search_scopus_full", tmp_path)
    assert d["source"] == "scopus_full"
    assert d["method"] == "MOCK"


def test_scopus_full_fallback_generates_md(tmp_path):
    d = _run_fallback("search_scopus_full", tmp_path)
    assert d["method"] == "FALLBACK_MD"
    md_path = Path(d["fallback_md_path"])
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "Scopus" in content
    assert "Periódicos CAPES" in content
    assert "CAFe" in content


def test_sciencedirect_full_mock(tmp_path):
    d = _run_mock("search_sciencedirect_full", tmp_path)
    assert d["source"] == "sciencedirect_full"


def test_embase_mock(tmp_path):
    d = _run_mock("search_embase", tmp_path)
    assert d["source"] == "embase"


# ============ R3 — Springer/Wiley/IEEE/WoS (4 adapters) ============

def test_springer_full_mock(tmp_path):
    d = _run_mock("search_springer_full", tmp_path)
    assert d["source"] == "springer_full"


def test_wiley_tdm_mock(tmp_path):
    d = _run_mock("search_wiley_tdm", tmp_path)
    assert d["source"] == "wiley_full"


def test_ieee_full_mock(tmp_path):
    d = _run_mock("search_ieee_full", tmp_path)
    assert d["source"] == "ieee_full"


def test_wos_full_mock(tmp_path):
    d = _run_mock("search_wos_full", tmp_path)
    assert d["source"] == "wos_full"


# ============ R4 — APA/CINAHL/JSTOR/Sage (4 adapters) ============

def test_psycinfo_full_mock(tmp_path):
    d = _run_mock("search_psycinfo_full", tmp_path)
    assert d["source"] == "psycinfo_full"


def test_cinahl_full_mock(tmp_path):
    d = _run_mock("search_cinahl_full", tmp_path)
    assert d["source"] == "cinahl_full"


def test_jstor_full_mock(tmp_path):
    d = _run_mock("search_jstor_full", tmp_path)
    assert d["source"] == "jstor_full"


def test_sage_full_mock(tmp_path):
    d = _run_mock("search_sage_full", tmp_path)
    assert d["source"] == "sage_full"


# ============ R5 — ACM/SSRN/Hein/ProQuest (4 adapters) ============

def test_acm_full_mock(tmp_path):
    d = _run_mock("search_acm_full", tmp_path)
    assert d["source"] == "acm_full"


def test_ssrn_full_mock(tmp_path):
    d = _run_mock("search_ssrn_full", tmp_path)
    assert d["source"] == "ssrn_full"


def test_hein_online_mock(tmp_path):
    d = _run_mock("search_hein_online", tmp_path)
    assert d["source"] == "hein_online"


def test_proquest_full_mock(tmp_path):
    d = _run_mock("search_proquest_full", tmp_path)
    assert d["source"] == "proquest_full"


def test_hein_online_fallback_generates_md(tmp_path):
    """HeinOnline sem chave + sem proxy → fallback .md."""
    d = _run_fallback("search_hein_online", tmp_path)
    assert d["method"] == "FALLBACK_MD"
    md_path = Path(d["fallback_md_path"])
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "Hein Online" in content or "hein_online" in content


# ============ R6 — Google Scholar via SerpApi (1 adapter) ============

def test_google_scholar_serpapi_mock(tmp_path):
    d = _run_mock("search_google_scholar_serpapi", tmp_path)
    assert d["source"] == "google_scholar"


def test_google_scholar_serpapi_fallback_generates_md(tmp_path):
    d = _run_fallback("search_google_scholar_serpapi", tmp_path)
    assert d["method"] == "FALLBACK_MD"


# ============ Integração ao orquestrador ============

def test_tier1_runners_has_16_paywall_adapters():
    """v2.15.0: 16 paywall adapters em TIER1_RUNNERS."""
    import search_orchestrator
    runners = search_orchestrator.TIER1_RUNNERS
    paywall_dbs = {
        "scopus_full", "sciencedirect_full", "embase",
        "springer_full", "wiley_full", "ieee_full", "wos_full",
        "psycinfo_full", "cinahl_full", "jstor_full", "sage_full",
        "acm_full", "ssrn_full", "hein_online", "proquest_full",
        "google_scholar",
    }
    missing = paywall_dbs - set(runners.keys())
    assert not missing, f"v2.15.0 paywall faltando em TIER1_RUNNERS: {missing}"


def test_tier1_runners_total_v2150():
    """v2.15.0: TIER1_RUNNERS deve ter 57 adapters (41 v2.11.0 + 16 paywall)."""
    import search_orchestrator
    n = len(search_orchestrator.TIER1_RUNNERS)
    assert n == 57, f"esperado 57 runners (41+16), encontrado {n}"


def test_all_v2150_runners_point_to_existing_files():
    """v2.15.0: todos os runners apontam para arquivos existentes."""
    import search_orchestrator
    scripts_dir = search_orchestrator.SCRIPTS_DIR
    for db, runner in search_orchestrator.TIER1_RUNNERS.items():
        path = scripts_dir / runner
        assert path.exists(), f"runner '{runner}' (db={db}) não existe em {path}"


def test_tier_databases_has_tier2_paywall_in_all_areas():
    """v2.15.0: cada área tem tier2_paywall populado."""
    import search_orchestrator
    for area, dbs in search_orchestrator.TIER_DATABASES.items():
        assert "tier2_paywall" in dbs, f"área {area} sem tier2_paywall"
        # Multi pode ter menos; outras devem ter pelo menos 2
        if area != "multi":
            assert len(dbs["tier2_paywall"]) >= 2, (
                f"área {area} com tier2_paywall vazio: {dbs['tier2_paywall']}"
            )


def test_priority_0_routing_emptied_for_implemented_dbs():
    """v2.15.0: bases que viraram tier2_paywall foram removidas de priority_0_routing."""
    import search_orchestrator
    for area, dbs in search_orchestrator.TIER_DATABASES.items():
        p0 = dbs.get("priority_0_routing", [])
        # Antes da v2.15.0, scopus/wos estavam em p0; agora estão em tier2_paywall
        assert "scopus" not in p0, f"{area}: 'scopus' ainda em priority_0_routing"
        assert "wos" not in p0, f"{area}: 'wos' ainda em priority_0_routing"


def test_disclosure_includes_tier2_paywall_section():
    """v2.15.0: disclosure menciona tier2_paywall e cascata."""
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "saude", "systematic_review_with_2_reviewers", 2020, 2026, "diabetes"
    )
    assert "Tier 2 paywall" in msg
    assert "KEY" in msg
    assert "PROXY" in msg
    assert "FALLBACK_MD" in msg or "citations_to_obtain" in msg


def test_disclosure_humanidades_has_jstor_full_paywall():
    """v2.15.0: humanidades tem JSTOR full e Hein Online em tier2_paywall."""
    import search_orchestrator
    h = search_orchestrator.TIER_DATABASES["humanidades"]
    assert "jstor_full" in h["tier2_paywall"]
    assert "hein_online" in h["tier2_paywall"]


def test_disclosure_cs_se_has_ieee_acm_paywall():
    """v2.15.0: cs_se tem IEEE e ACM full em tier2_paywall."""
    import search_orchestrator
    c = search_orchestrator.TIER_DATABASES["cs_se"]
    assert "ieee_full" in c["tier2_paywall"]
    assert "acm_full" in c["tier2_paywall"]


def test_disclosure_ciencias_sociais_has_ssrn_paywall():
    """v2.15.0: ciencias_sociais tem SSRN em tier2_paywall (estava em unimplementable)."""
    import search_orchestrator
    cs = search_orchestrator.TIER_DATABASES["ciencias_sociais"]
    assert "ssrn_full" in cs["tier2_paywall"]


# ============ Fallback .md cross-search ============

def test_fallback_md_includes_capes_instructions(tmp_path):
    """Fallback .md inclui 4 opções de obtenção (CAFe, biblioteca, autor, COMUT)."""
    d = _run_fallback("search_scopus_full", tmp_path)
    md_content = Path(d["fallback_md_path"]).read_text(encoding="utf-8")
    assert "Periódicos CAPES" in md_content
    assert "biblioteca da sua instituição" in md_content
    assert "autor correspondente" in md_content
    assert "COMUT" in md_content


def test_fallback_md_includes_query_metadata(tmp_path):
    """Fallback .md inclui query original e janela temporal."""
    out = tmp_path / "test.json"
    cmd = [sys.executable, str(ROOT / "scripts/searches/search_acm_full.py"),
           "--query", "machine learning fairness", "--year-start", "2022",
           "--year-end", "2024", "--output", str(out),
           "--output-dir", str(tmp_path)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    md_path = tmp_path / "citations_to_obtain_acm_full.md"
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "machine learning fairness" in content
    assert "2022-2024" in content


# ============ Smoke real do orquestrador ============

def test_orchestrator_runs_paywall_searches_in_multi(tmp_path):
    """Orquestrador chama run_tier2_paywall_searches e gera fallback .md."""
    import search_orchestrator
    files = search_orchestrator.run_tier2_paywall_searches(
        "multi", "test", 2023, 2024, str(tmp_path)
    )
    # Para "multi", tier2_paywall = [scopus_full, wos_full, google_scholar]
    assert len(files) == 3
    # Cada um gerou results_*.json E o fallback .md
    for db in ["scopus_full", "wos_full", "google_scholar"]:
        assert (tmp_path / f"results_{db}.json").exists()
        assert (tmp_path / f"citations_to_obtain_{db}.md").exists()
