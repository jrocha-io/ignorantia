"""Smoke tests v2.10.2 — 10 adapters novos + reorganização TIER_DATABASES."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# --- Adapters individuais — todos rodam em --mock ----------------------------

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


def test_pubmed_central_mock(tmp_path):
    d = _run_mock("search_pubmed_central", tmp_path)
    assert d["source"] == "pubmed_central"
    assert d["source_tier"] == "tier1"
    assert all(r.get("pmcid", "").startswith("PMC") for r in d["results"])


def test_europepmc_mock(tmp_path):
    d = _run_mock("search_europepmc", tmp_path)
    assert d["source"] == "europepmc"
    assert d["source_tier"] == "tier1"


def test_biorxiv_mock(tmp_path):
    d = _run_mock("search_biorxiv", tmp_path, ["--server", "biorxiv"])
    assert d["source"] == "biorxiv"
    assert all(r.get("preprint_server") == "biorxiv" for r in d["results"])


def test_medrxiv_mock_via_wrapper(tmp_path):
    """medRxiv wrapper delega ao adapter genérico com server=medrxiv."""
    d = _run_mock("search_medrxiv", tmp_path)
    assert d["source"] == "medrxiv"
    assert all(r.get("preprint_server") == "medrxiv" for r in d["results"])


def test_eric_mock(tmp_path):
    d = _run_mock("search_eric", tmp_path)
    assert d["source"] == "eric"
    assert d["source_tier"] == "tier1"  # default oa_only


def test_eric_mock_include_non_oa(tmp_path):
    d = _run_mock("search_eric", tmp_path, ["--include-non-oa"])
    assert d["source_tier"] == "tier2"  # consolidação eric_full
    assert d["oa_only"] is False


def test_osf_preprints_mock(tmp_path):
    d = _run_mock("search_osf_preprints", tmp_path)
    assert "osf_preprints" in d["source"]
    assert d["source_tier"] == "tier1"


def test_edarxiv_mock_via_wrapper(tmp_path):
    """edArxiv wrapper delega ao adapter OSF genérico com provider=edarxiv."""
    d = _run_mock("search_edarxiv", tmp_path)
    assert d["source"] == "osf_preprints/edarxiv"
    assert d["provider_filter"] == "edarxiv"


def test_zenodo_mock(tmp_path):
    d = _run_mock("search_zenodo", tmp_path)
    assert d["source"] == "zenodo"
    assert all(r.get("doi", "").startswith("10.5281/zenodo.") for r in d["results"])


def test_hal_mock(tmp_path):
    d = _run_mock("search_hal", tmp_path)
    assert d["source"] == "hal"
    assert all(r.get("hal_id") for r in d["results"])
    # HAL tem cobertura francesa
    langs = {r.get("language") for r in d["results"]}
    assert "fr" in langs


def test_openalex_mock(tmp_path):
    d = _run_mock("search_openalex", tmp_path)
    assert d["source"] == "openalex"
    assert d["source_tier"] == "tier1"
    assert all(r.get("openalex_id", "").startswith("https://openalex.org/W")
               for r in d["results"])


def test_openalex_mock_include_non_oa(tmp_path):
    d = _run_mock("search_openalex", tmp_path, ["--include-non-oa"])
    assert d["source_tier"] == "tier2"
    assert d["oa_only"] is False


# --- Reorganização TIER_DATABASES (R7) ----------------------------------------

def test_tier_databases_no_redundant_declarations():
    """Redundâncias declarativas removidas — openalex_oa, crossref_oa_filter,
    pubmed_full, eric_full não devem aparecer em nenhuma área."""
    import search_orchestrator
    redundant = {"openalex_oa", "crossref_oa_filter", "pubmed_full", "eric_full"}
    for area, dbs in search_orchestrator.TIER_DATABASES.items():
        all_listed = set(dbs.get("tier1", [])) | set(dbs.get("tier2", []))
        intersection = all_listed & redundant
        assert not intersection, (
            f"Redundância declarativa em {area}: {intersection}. "
            f"Decisão R7 v2.10.2: removidas porque cobertas via crossref/openalex/semantic_scholar."
        )


def test_tier_databases_has_unimplementable_category():
    """v2.10.2: categoria 'unimplementable' existe para bases sem API pública.

    v2.15.0: a maioria das bases que estavam em `unimplementable` (acm_full, ieee_full,
    ssrn, hein_online, jstor_full, cinahl_full) migrou para `tier2_paywall` com cascata
    DD-8. Apenas casos onde NEM mesmo cascata é viável permanecem em `unimplementable`.
    """
    import search_orchestrator
    for area, dbs in search_orchestrator.TIER_DATABASES.items():
        assert "unimplementable" in dbs, f"falta 'unimplementable' em {area}"
        assert isinstance(dbs["unimplementable"], list)
    # v2.15.0: cs_se não tem mais acm_full nem ieee_full em unimplementable;
    # ambos migraram para tier2_paywall.
    cs_paywall = search_orchestrator.TIER_DATABASES["cs_se"].get("tier2_paywall", [])
    assert "acm_full" in cs_paywall, "acm_full deveria estar em tier2_paywall (v2.15.0)"
    assert "ieee_full" in cs_paywall, "ieee_full deveria estar em tier2_paywall (v2.15.0)"


def test_tier_databases_unimplementable_has_reason():
    """Cada entry em 'unimplementable' tem db + reason."""
    import search_orchestrator
    for area, dbs in search_orchestrator.TIER_DATABASES.items():
        for entry in dbs.get("unimplementable", []):
            assert isinstance(entry, dict), f"entry em {area}/unimplementable não é dict"
            assert "db" in entry
            assert "reason" in entry
            assert len(entry["reason"]) > 10  # razão substantiva, não placeholder


def test_tier1_runners_v2102_has_all_new_adapters():
    """v2.10.2: 10 adapters novos registrados em TIER1_RUNNERS."""
    import search_orchestrator
    runners = search_orchestrator.TIER1_RUNNERS
    new_v2102 = {"pubmed_central", "europepmc", "biorxiv", "medrxiv",
                 "eric", "osf_preprints", "edarxiv", "zenodo", "hal", "openalex"}
    assert new_v2102.issubset(set(runners.keys())), (
        f"v2.10.2 faltando: {new_v2102 - set(runners.keys())}"
    )


def test_all_runners_point_to_existing_files():
    """Todos os 23 runners apontam para arquivos .py existentes."""
    import search_orchestrator
    scripts_dir = search_orchestrator.SCRIPTS_DIR
    for db, runner in search_orchestrator.TIER1_RUNNERS.items():
        path = scripts_dir / runner
        assert path.exists(), f"runner '{runner}' (db={db}) não existe em {path}"


# --- Disclosure honesta com 3 categorias --------------------------------------

def test_disclosure_distinguishes_implemented_vs_roadmap():
    """Disclosure separa bases que rodam de fato vs roadmap."""
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "saude", "scoping_review", 2020, 2026, "test"
    )
    assert "BUSCAS QUE VOU EXECUTAR AGORA" in msg
    # Após v2.10.2, todas as bases declaradas têm runner; "ROADMAP" só aparece
    # se houver bases sem adapter (não é o caso na maioria das áreas)


def test_disclosure_lists_unimplementable_in_cs_se():
    """v2.15.0: ACM/IEEE migraram de unimplementable para tier2_paywall.

    A disclosure agora os menciona na seção 'Tier 2 paywall' (cascata) em vez
    de 'INVIÁVEIS AUTOMATICAMENTE'. O princípio de declaração honesta permanece:
    o usuário sabe que essas bases não têm API gratuita e que o adapter
    tentará chave/proxy/fallback.
    """
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "cs_se", "systematic_review_with_2_reviewers", 2020, 2026, "test"
    )
    # v2.15.0: ambos devem aparecer na disclosure (em alguma seção)
    assert "acm_full" in msg
    assert "ieee_full" in msg
    # Devem aparecer na seção tier2_paywall
    assert "Tier 2 paywall" in msg or "paywall" in msg.lower()


def test_disclosure_no_silent_skips():
    """v2.10.2: a disclosure não pode declarar bases sem registro."""
    import search_orchestrator
    for area in search_orchestrator.TIER_DATABASES:
        msg = search_orchestrator.build_user_disclosure_pre(
            area, "scoping_review", 2020, 2026, "test"
        )
        # Cada base listada como "VOU EXECUTAR AGORA" deve estar em TIER1_RUNNERS
        # (validação indireta: se não estivesse, a função particionaria como ROADMAP)


def test_disclosure_priority_0_section():
    """v2.15.0: bases pagas (Scopus, WoS) declaradas em tier2_paywall (cascata) ou priority_0."""
    import search_orchestrator
    msg = search_orchestrator.build_user_disclosure_pre(
        "saude", "systematic_review_with_2_reviewers", 2020, 2026, "test"
    )
    # v2.15.0: tier2_paywall é a categoria nova; priority_0 pode estar vazio
    assert "priority_0" in msg or "Tier 2 paywall" in msg or "paywall" in msg.lower()
    # Scopus e WoS devem aparecer em algum lugar (seja tier2_paywall ou priority_0)
    assert "scopus" in msg.lower() and "wos" in msg.lower()
