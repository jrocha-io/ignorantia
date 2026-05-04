"""Smoke tests v2.11.0 — 19 adapters premium + reorganização TIER_DATABASES."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


def _run_mock(adapter: str, tmp_path, extra_args: list = None) -> dict:
    import json
    out = tmp_path / f"{adapter}.json"
    cmd = [sys.executable, str(ROOT / f"scripts/searches/{adapter}.py"),
           "--query", "letramento digital", "--mock", "--output", str(out)]
    if extra_args:
        cmd.extend(extra_args)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert res.returncode == 0, f"{adapter} --mock falhou: {res.stderr}"
    return json.loads(out.read_text(encoding="utf-8"))


# ============ MUSTs (5) ============

def test_pubmed_mock(tmp_path):
    """v2.11.0 MUST: PubMed completo (não só PMC)."""
    d = _run_mock("search_pubmed", tmp_path)
    assert d["source"] == "pubmed"
    assert d["source_tier"] == "tier2"  # Tier 2 = metadados livres
    assert all(r.get("pmid") for r in d["results"])


def test_cochrane_central_mock(tmp_path):
    """v2.11.0 MUST: Cochrane CENTRAL Register."""
    d = _run_mock("search_cochrane_central", tmp_path)
    assert d["source"] == "cochrane_central"
    assert d["source_tier"] == "tier1"
    assert all("Randomized" in (r.get("study_type") or "") for r in d["results"])


def test_clinicaltrials_gov_mock(tmp_path):
    """v2.11.0 MUST: ClinicalTrials.gov."""
    d = _run_mock("search_clinicaltrials_gov", tmp_path)
    assert d["source"] == "clinicaltrials_gov"
    assert all(r.get("nct_id", "").startswith("NCT") for r in d["results"])


def test_oapen_mock(tmp_path):
    """v2.11.0 MUST: livros OA peer-reviewed."""
    d = _run_mock("search_oapen", tmp_path)
    assert d["source"] == "oapen"
    assert all(r.get("resource_type") == "book" for r in d["results"])


def test_dimensions_mock(tmp_path):
    """v2.11.0 MUST: indicadores bibliométricos (FWCI, Altmetric)."""
    d = _run_mock("search_dimensions", tmp_path)
    assert d["source"] == "dimensions"
    assert all("fwci" in r for r in d["results"])
    assert all("altmetric_score" in r for r in d["results"])


# ============ SHOULDs (6) ============

def test_jstor_oa_mock(tmp_path):
    """v2.11.0 SHOULD: JSTOR Open Content."""
    d = _run_mock("search_jstor_oa", tmp_path)
    assert d["source"] == "jstor_oa"


def test_scielo_preprints_mock(tmp_path):
    """v2.11.0 SHOULD: medRxiv lusófono."""
    d = _run_mock("search_scielo_preprints", tmp_path)
    assert d["source"] == "scielo_preprints"
    # SciELO Preprints serve LATAM com PT/EN
    langs = {r.get("language") for r in d["results"]}
    assert "pt" in langs or "en" in langs


def test_dialnet_mock(tmp_path):
    """v2.11.0 SHOULD: hispano-americano humanidades/direito."""
    d = _run_mock("search_dialnet", tmp_path)
    assert d["source"] == "dialnet"


def test_pepsic_mock(tmp_path):
    """v2.11.0 SHOULD: psicologia BR/LATAM."""
    d = _run_mock("search_pepsic", tmp_path)
    assert d["source"] == "pepsic"
    assert all(r.get("subject_area") == "psicologia" for r in d["results"])


def test_catalogo_teses_capes_mock(tmp_path):
    """v2.11.0 SHOULD: catálogo CAPES (teses BR oficiais)."""
    d = _run_mock("search_catalogo_teses_capes", tmp_path)
    assert d["source"] == "catalogo_teses_capes"
    assert all(r.get("country") == "BR" for r in d["results"])


def test_engineering_village_mock(tmp_path):
    """v2.11.0 SHOULD: engenharia (Compendex OA subset via OpenAlex)."""
    d = _run_mock("search_engineering_village", tmp_path)
    assert d["source"] == "engineering_village"
    assert all(r.get("via_index") == "compendex_oa_subset" for r in d["results"])


# ============ COULDs (7+) ============

def test_grey_lit_unesco_mock(tmp_path):
    """v2.11.0 COULD: literatura cinza UNESCO."""
    d = _run_mock("search_grey_lit", tmp_path, ["--provider", "unesco"])
    assert "grey_lit/unesco" in d["source"]


def test_grey_lit_world_bank_mock(tmp_path):
    """v2.11.0 COULD: literatura cinza World Bank."""
    d = _run_mock("search_grey_lit", tmp_path, ["--provider", "world_bank"])
    assert "grey_lit/world_bank" in d["source"]


def test_grey_lit_who_mock(tmp_path):
    """v2.11.0 COULD: literatura cinza WHO."""
    d = _run_mock("search_grey_lit", tmp_path, ["--provider", "who"])
    assert "grey_lit/who" in d["source"]


def test_philarchive_mock(tmp_path):
    """v2.11.0 COULD: filosofia OA."""
    d = _run_mock("search_philarchive", tmp_path)
    assert d["source"] == "philarchive"


def test_spell_mock(tmp_path):
    """v2.11.0 COULD: business research BR."""
    d = _run_mock("search_spell", tmp_path)
    assert d["source"] == "spell"


def test_redib_mock(tmp_path):
    """v2.11.0 COULD: ibero-americana complementar."""
    d = _run_mock("search_redib", tmp_path)
    assert d["source"] == "redib"


def test_e_lis_mock(tmp_path):
    """v2.11.0 COULD: biblioteconomia/CI."""
    d = _run_mock("search_e_lis", tmp_path)
    assert d["source"] == "e_lis"


def test_proquest_oa_mock(tmp_path):
    """v2.11.0 COULD: ProQuest subset OA."""
    d = _run_mock("search_proquest_oa", tmp_path)
    assert d["source"] == "proquest_oa"


def test_dabi_mock(tmp_path):
    """v2.11.0 COULD: educação nórdica."""
    d = _run_mock("search_dabi", tmp_path)
    assert d["source"] == "dabi"


def test_jane_classifier_mock(tmp_path):
    """v2.11.0 utilitário Fase 8: classificador de venue (não busca)."""
    import json
    out = tmp_path / "jane.json"
    cmd = [sys.executable, str(ROOT / "scripts/searches/search_jane.py"),
           "--text", "Digital health literacy in older adults: a systematic review",
           "--mock", "--output", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert res.returncode == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["source"] == "jane"
    assert d["source_tier"] == "venue_classifier"  # NÃO é tier de busca
    assert "n_journal_suggestions" in d


# ============ Reorganização TIER_DATABASES (v2.11.0) ============

def test_tier_databases_has_humanities_area():
    """v2.11.0+: nova área 'humanidades' criada. v2.15.0: hein_online migrou para tier2_paywall."""
    import search_orchestrator
    assert "humanidades" in search_orchestrator.TIER_DATABASES
    h = search_orchestrator.TIER_DATABASES["humanidades"]
    # Humanidades = livros OA primários + JSTOR + filosofia
    assert "oapen" in h["tier1"]
    assert "jstor_oa" in h["tier1"]
    assert "philarchive" in h["tier1"]
    # v2.15.0: HeinOnline migrou de unimplementable para tier2_paywall (cascata)
    assert "hein_online" in h["tier2_paywall"]


def test_tier_databases_has_business_area():
    """v2.11.0: nova área 'business' criada."""
    import search_orchestrator
    assert "business" in search_orchestrator.TIER_DATABASES
    b = search_orchestrator.TIER_DATABASES["business"]
    # Business research BR = Spell + REDIB + OAPEN
    assert "spell" in b["tier1"]
    assert "redib" in b["tier1"]
    assert "oapen" in b["tier1"]
    # EBSCO Business Source declarado inviável
    unimpl_dbs = {u["db"] for u in b["unimplementable"]}
    assert "ebsco_business_source" in unimpl_dbs


def test_saude_has_premium_health_trio():
    """v2.11.0: saúde tem o tripé Cochrane + ClinicalTrials + PubMed."""
    import search_orchestrator
    s = search_orchestrator.TIER_DATABASES["saude"]
    assert "cochrane_central" in s["tier1"]
    assert "clinicaltrials_gov" in s["tier1"]
    assert "pubmed" in s["tier2"]


def test_saude_includes_oapen_books():
    """v2.11.0: livros OA cobertos em saúde também (especialmente para metodologia)."""
    import search_orchestrator
    s = search_orchestrator.TIER_DATABASES["saude"]
    assert "oapen" in s["tier1"]


def test_dimensions_in_tier2_for_metric_areas():
    """v2.11.0: Dimensions (FWCI, Altmetric) presente em áreas onde indicadores importam."""
    import search_orchestrator
    metric_areas = ["saude", "educacao", "cs_se", "ciencias_sociais", "business", "multi"]
    for area in metric_areas:
        assert "dimensions" in search_orchestrator.TIER_DATABASES[area]["tier2"], (
            f"Dimensions ausente em {area}/tier2"
        )


def test_engineering_in_cs_se():
    """v2.11.0: engineering_village adicionado a cs_se."""
    import search_orchestrator
    assert "engineering_village" in search_orchestrator.TIER_DATABASES["cs_se"]["tier1"]


def test_grey_lit_in_multi():
    """v2.11.0: grey_lit em multi para realist reviews + white papers."""
    import search_orchestrator
    assert "grey_lit" in search_orchestrator.TIER_DATABASES["multi"]["tier1"]


# ============ TIER1_RUNNERS contém todos os 18 novos (jane fica fora) ============

def test_tier1_runners_v2110_premium_18_added():
    """v2.11.0: 18 adapters premium em TIER1_RUNNERS (jane = classificador, fora)."""
    import search_orchestrator
    runners = search_orchestrator.TIER1_RUNNERS
    new_v2110 = {
        # MUSTs
        "pubmed", "cochrane_central", "clinicaltrials_gov", "oapen", "dimensions",
        # SHOULDs
        "jstor_oa", "scielo_preprints", "dialnet", "pepsic", "catalogo_teses_capes",
        "engineering_village",
        # COULDs (7 buscáveis; jane fica fora)
        "grey_lit", "philarchive", "spell", "redib", "e_lis", "proquest_oa", "dabi",
    }
    missing = new_v2110 - set(runners.keys())
    assert not missing, f"v2.11.0 faltando em TIER1_RUNNERS: {missing}"
    # jane NÃO deve estar em TIER1_RUNNERS
    assert "jane" not in runners, "jane é classificador de venue, não deve estar em TIER1_RUNNERS"


def test_all_v2110_runners_point_to_existing_files():
    """v2.11.0: todos os runners apontam para arquivos .py existentes."""
    import search_orchestrator
    scripts_dir = search_orchestrator.SCRIPTS_DIR
    for db, runner in search_orchestrator.TIER1_RUNNERS.items():
        path = scripts_dir / runner
        assert path.exists(), f"runner '{runner}' (db={db}) não existe em {path}"


def test_tier1_runners_total_count_v2110():
    """v2.11.0: TIER1_RUNNERS deve ter ≥41 adapters. v2.15.0 expandiu para 57 (+16 paywall)."""
    import search_orchestrator
    n = len(search_orchestrator.TIER1_RUNNERS)
    # v2.11.0 exigia 41; v2.15.0 expandiu para 57 — verificamos limite mínimo da v2.11.0
    assert n >= 41, f"esperado ≥41 runners (estado v2.11.0), encontrado {n}"


# ============ Disclosure honesta para áreas novas ============

def test_disclosure_humanidades_lists_oapen_jstor_philarchive():
    """v2.11.0: disclosure de humanidades menciona livros + JSTOR + filosofia."""
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "humanidades", "scoping_review", 2020, 2026, "filosofia da mente"
    )
    assert "oapen" in msg
    assert "jstor_oa" in msg
    assert "philarchive" in msg


def test_disclosure_business_lists_spell_oapen_redib():
    """v2.11.0: disclosure de business menciona Spell + OAPEN + REDIB."""
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "business", "rapid_review", 2020, 2026, "transformação digital"
    )
    assert "spell" in msg
    assert "oapen" in msg
    assert "redib" in msg


def test_disclosure_saude_lists_premium_health_trio():
    """v2.11.0: disclosure de saúde menciona Cochrane + ClinicalTrials."""
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "saude", "systematic_review_with_2_reviewers", 2020, 2026, "diabetes type 2"
    )
    assert "cochrane_central" in msg
    assert "clinicaltrials_gov" in msg
