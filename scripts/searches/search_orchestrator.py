#!/usr/bin/env python3
"""
search_orchestrator.py — Orquestrador de busca multi-base com política OA-first (3 tiers).

Implementa a constraint operacional v2.1 do ignorantia:
- Tier 1 (sempre OA): busca SEMPRE; busca primeiro.
- Tier 2 (metadados livres): busca SEMPRE; declara limitações de full-text.
- Bases de alta relevância (priority_0_routing): tentadas via Tier 0 (Unpaywall + OAB + CORE
  + Periódicos CAPES com CAFe se disponível). O que sobrar entra no gap_report.md (Decisão 24).

Usage:
    python search_orchestrator.py --query "letramento digital idosos" \\
                                  --year-start 2020 --year-end 2026 \\
                                  --area saude \\
                                  --mode scoping_review \\
                                  --output-dir search_results/

Modes recognized: scoping_review, rapid_review, mapping_study,
                  systematic_review_with_2_reviewers, integrative_review, realist_review

Areas recognized: saude, educacao, cs_se, multi
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# Mapeamento de bases por (área, tier)
#
# Decisão 24 (v2.9.0): "tier3" foi renomeado para "priority_0_routing".
# Não é mais uma "lacuna aceitável" se o usuário não tem acesso institucional.
# As bases listadas aqui são tentadas via Tier 0 (Unpaywall + OAB + CORE +
# Periódicos CAPES com CAFe quando disponível); o que sobrar entra no gap_report.md.
#
# Decisão 25 (v2.9.0): bases ibero-americanas e multilíngues são OBRIGATÓRIAS
# em todas as áreas, não específicas a "saude" ou "educacao". A skill suporta
# pt-BR + es-LA + en por design (Decisão 27 — obrigação, não limitação).
TIER_DATABASES = {
    "saude": {
        "tier1": [
            # OA primárias (NIH/EBI + preprint servers de saúde)
            "pubmed_central", "europepmc", "medrxiv", "biorxiv",
            # Tripé canônico Cochrane Handbook (v2.11.0 premium)
            "cochrane_central", "clinicaltrials_gov",
            # Ibero-americanas obrigatórias (Decisão 25)
            "scielo", "scielo_preprints", "lilacs", "la_referencia", "redalyc", "bdtd",
            "catalogo_teses_capes",
            # Multilíngue (CORE + DOAJ)
            "doaj", "core",
            # Premium: livros OA + venue classifier indireto
            "oapen",
        ],
        # Tier 2: PubMed completo + bibliométricos
        "tier2": ["pubmed", "crossref", "openalex", "semantic_scholar", "dimensions"],
        # Tier 2 paywall com cascata KEY→PROXY→FALLBACK_MD (v2.12-v2.16)
        "tier2_paywall": ["scopus_full", "wos_full", "embase", "cinahl_full",
                          "sciencedirect_full", "google_scholar"],
        "priority_0_routing": [],  # bases anteriormente aqui agora têm cascata
        "unimplementable": [],
    },
    "educacao": {
        "tier1": [
            "eric", "edarxiv",
            "scielo", "scielo_preprints", "la_referencia", "redalyc", "clacso",
            "bdtd", "catalogo_teses_capes",
            "doaj", "core",
            # Premium: livros OA + cobertura ibérica + nórdica
            "oapen", "dialnet", "dabi",
        ],
        "tier2": ["crossref", "openalex", "semantic_scholar", "dimensions"],
        "tier2_paywall": ["scopus_full", "wos_full", "psycinfo_full",
                          "sciencedirect_full", "sage_full", "google_scholar",
                          "proquest_full"],
        "priority_0_routing": [],
        "unimplementable": [],
    },
    "cs_se": {
        "tier1": [
            "arxiv", "dblp", "hal",
            "scielo", "la_referencia", "bdtd",
            "doaj", "core", "openalex",
            # Premium: livros OA + engenharia
            "oapen", "engineering_village",
        ],
        "tier2": ["crossref", "semantic_scholar", "dimensions"],
        "tier2_paywall": ["scopus_full", "wos_full", "ieee_full", "acm_full",
                          "sciencedirect_full", "springer_full", "wiley_full",
                          "google_scholar"],
        "priority_0_routing": [],
        "unimplementable": [],
    },
    "ciencias_sociais": {
        "tier1": [
            "scielo", "scielo_preprints", "la_referencia", "redalyc", "clacso",
            "bdtd", "scioteca", "catalogo_teses_capes",
            "doaj", "core", "osf_preprints",
            # Premium: livros OA + JSTOR OA + ibérico + filosofia (overlap)
            "oapen", "jstor_oa", "dialnet", "philarchive",
        ],
        "tier2": ["crossref", "openalex", "semantic_scholar", "dimensions"],
        "tier2_paywall": ["scopus_full", "wos_full", "jstor_full", "sage_full",
                          "ssrn_full", "google_scholar"],
        "priority_0_routing": [],
        "unimplementable": [],
    },
    "humanidades": {
        # v2.11.0: nova área dedicada para humanidades
        # (filosofia, literatura, história, artes, religião)
        "tier1": [
            "scielo", "scielo_preprints", "la_referencia", "redalyc", "bdtd",
            "catalogo_teses_capes",
            "doaj", "core",
            # Humanidades é onde JSTOR OA + OAPEN são primários (livro = unidade primária)
            "oapen", "jstor_oa", "philarchive", "dialnet",
            # Bibliotec/CI nicho
            "e_lis",
        ],
        "tier2": ["crossref", "openalex", "semantic_scholar"],
        "tier2_paywall": ["scopus_full", "wos_full", "jstor_full", "hein_online",
                          "sage_full", "google_scholar"],
        "priority_0_routing": [],
        "unimplementable": [],
    },
    "business": {
        # v2.11.0: nova área para administração, contabilidade, gestão pública
        "tier1": [
            "scielo", "la_referencia", "redalyc", "bdtd", "catalogo_teses_capes",
            "doaj", "core",
            # Premium: business research BR + bibliométricos
            "spell", "oapen", "redib",
        ],
        "tier2": ["crossref", "openalex", "semantic_scholar", "dimensions"],
        "tier2_paywall": ["scopus_full", "wos_full", "ssrn_full", "sage_full",
                          "wiley_full", "google_scholar", "proquest_full"],
        "priority_0_routing": [],
        "unimplementable": [
            {"db": "ebsco_business_source",
             "reason": "EBSCO Business Source full requer credencial institucional ativa; sem API individual pública. Recomenda-se PROXY institucional ou search_spell.py para BR."},
        ],
    },
    "multi": {
        "tier1": [
            "doaj", "osf_preprints", "zenodo",
            "scielo", "scielo_preprints", "la_referencia", "redalyc", "bdtd", "core",
            "catalogo_teses_capes",
            # Premium: livros OA + bibliométricos + grey lit
            "oapen", "grey_lit",
        ],
        "tier2": ["crossref", "openalex", "semantic_scholar", "dimensions"],
        "tier2_paywall": ["scopus_full", "wos_full", "google_scholar"],
        "priority_0_routing": [],
        "unimplementable": [],
    },
}

# Backward-compat: aliases temporários para código que ainda lê "tier3".
# Removidos em v2.10.0.
for _area in TIER_DATABASES:
    TIER_DATABASES[_area]["tier3"] = TIER_DATABASES[_area].get("priority_0_routing", [])

# Mapeamento de modos para política mínima de tiers
MODE_TIER_POLICY = {
    "scoping_review": {
        "tier1_min_databases": 3,
        "tier2_recommended": True,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
    "rapid_review": {
        "tier1_min_databases": 1,
        "tier2_recommended": False,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
    "mapping_study": {
        "tier1_min_databases": 3,
        "tier2_recommended": True,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,  # frequentemente exigido em CS/SE
    },
    "systematic_review_with_2_reviewers": {
        "tier1_min_databases": 3,
        "tier2_recommended": True,
        "tier3_required": True,  # alias retro-compat — semantica real: priority_0_required
        "priority_0_via_tier0_routing": True,
    },
    "integrative_review": {
        "tier1_min_databases": 3,
        "tier2_recommended": True,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
    "realist_review": {
        "tier1_min_databases": 3,
        "tier2_recommended": True,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
    # Modos secundários — pesquisa bibliográfica não é o produto principal
    "software_paper": {
        "tier1_min_databases": 0,  # 5-15 refs comparativas curadas
        "tier2_recommended": False,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
    "position_paper": {
        "tier1_min_databases": 1,  # busca complementar para fundamentar argumentação
        "tier2_recommended": True,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
    "technical_report": {
        "tier1_min_databases": 0,
        "tier2_recommended": False,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
    "white_paper": {
        "tier1_min_databases": 1,
        "tier2_recommended": True,
        "tier3_required": False,
        "priority_0_via_tier0_routing": True,
    },
}

# Backward-compat: aliases para chaves renomeadas em v2.9.0/v2.10.1.
# Removidos em v2.11.0.
for _mode in MODE_TIER_POLICY:
    MODE_TIER_POLICY[_mode]["tier3_via_user_only"] = MODE_TIER_POLICY[_mode].get(
        "priority_0_via_tier0_routing", True
    )
    MODE_TIER_POLICY[_mode]["priority_0_required"] = MODE_TIER_POLICY[_mode].get(
        "tier3_required", False
    )

SCRIPTS_DIR = Path(__file__).parent
TIER1_RUNNERS = {
    # Adapters originais (v2.0.x — v2.5.x)
    "arxiv": "search_arxiv.py",
    "scielo": "search_scielo.py",
    "dblp": "search_dblp.py",
    "crossref": "search_crossref.py",
    "semantic_scholar": "search_semantic_scholar.py",
    # Ibero-americanos (v2.9.0 — Decisão 25)
    "la_referencia": "search_la_referencia.py",
    "redalyc": "search_redalyc.py",
    "clacso": "search_clacso.py",
    "bdtd": "search_bdtd.py",
    "scioteca": "search_scioteca.py",
    # Multilíngue (v2.9.0 + v2.10.1)
    "doaj": "search_doaj.py",
    "lilacs": "search_lilacs.py",
    "core": "search_core.py",
    # NCBI/EBI biomédicas (v2.10.2 R1)
    "pubmed_central": "search_pubmed_central.py",
    "europepmc": "search_europepmc.py",
    # Preprint servers de saúde (v2.10.2 R2)
    "biorxiv": "search_biorxiv.py",
    "medrxiv": "search_medrxiv.py",
    # Educação (v2.10.2 R3 + R4)
    "eric": "search_eric.py",
    "edarxiv": "search_edarxiv.py",
    # Multi-disciplinar (v2.10.2 R4 + R5 + R6)
    "osf_preprints": "search_osf_preprints.py",
    "zenodo": "search_zenodo.py",
    "hal": "search_hal.py",
    "openalex": "search_openalex.py",
    # ============ v2.11.0 PREMIUM TIER ============
    # MUSTs de saúde (PRISMA-2020 + Cochrane Handbook canonical)
    "pubmed": "search_pubmed.py",
    "cochrane_central": "search_cochrane_central.py",
    "clinicaltrials_gov": "search_clinicaltrials_gov.py",
    # MUSTs multi-disciplinar
    "oapen": "search_oapen.py",
    "dimensions": "search_dimensions.py",
    # SHOULDs (cobertura por área específica + LATAM completo)
    "jstor_oa": "search_jstor_oa.py",
    "scielo_preprints": "search_scielo_preprints.py",
    "dialnet": "search_dialnet.py",
    "pepsic": "search_pepsic.py",
    "catalogo_teses_capes": "search_catalogo_teses_capes.py",
    "engineering_village": "search_engineering_village.py",
    # COULDs (nicho + grey lit)
    "grey_lit": "search_grey_lit.py",  # genérico multi-provider
    "philarchive": "search_philarchive.py",
    "spell": "search_spell.py",
    "redib": "search_redib.py",
    "e_lis": "search_e_lis.py",
    "proquest_oa": "search_proquest_oa.py",
    "dabi": "search_dabi.py",
    # ============ v2.12-v2.16 PAYWALL ADAPTERS COM CASCATA ============
    # DD-7 + DD-8: cada adapter implementa cascata KEY → PROXY → FALLBACK_MD.
    # Sem credencial (chave ou proxy), gera citations_to_obtain_<source>.md.
    # R2 v2.12.0 — Elsevier (3)
    "scopus_full": "search_scopus_full.py",
    "sciencedirect_full": "search_sciencedirect_full.py",
    "embase": "search_embase.py",
    # R3 v2.13.0 — Outros publishers grandes (4)
    "springer_full": "search_springer_full.py",
    "wiley_full": "search_wiley_tdm.py",
    "ieee_full": "search_ieee_full.py",
    "wos_full": "search_wos_full.py",
    # R4 v2.14.0 — APA/EBSCO/JSTOR/Sage (4)
    "psycinfo_full": "search_psycinfo_full.py",
    "cinahl_full": "search_cinahl_full.py",
    "jstor_full": "search_jstor_full.py",
    "sage_full": "search_sage_full.py",
    # R5 v2.15.0 — Sem API pública (4)
    "acm_full": "search_acm_full.py",
    "ssrn_full": "search_ssrn_full.py",
    "hein_online": "search_hein_online.py",
    "proquest_full": "search_proquest_full.py",
    # R6 v2.16.0 — Google Scholar via SerpApi (1)
    "google_scholar": "search_google_scholar_serpapi.py",
    # NÃO no dict (intencional):
    # - "periodicos_capes": gateway com instruções acionáveis (Decisão 24)
    # - "jane": classificador de venue para Fase 8, não adapter de busca
    # - "researchgate", "academia.edu": WON'T por DD-6 (ToS proíbe scraping)
}


def build_user_disclosure_pre(area, mode, year_start, year_end, query):
    """Mensagem de transparência ANTES da busca.

    v2.15.0: quatro categorias honestas:
    1. Tier 1 (OA gratuito, full-text) — rodam sempre.
    2. Tier 2 (metadados livres) — rodam sempre.
    3. Tier 2 paywall (cascata KEY→PROXY→FALLBACK_MD) — adapter v2.12-v2.16.
    4. Inviáveis automaticamente — declaradas como gap.
    """
    pol = MODE_TIER_POLICY[mode]
    dbs = TIER_DATABASES[area]
    p0 = dbs.get("priority_0_routing", dbs.get("tier3", []))
    unimpl = dbs.get("unimplementable", [])
    tier2_paywall = dbs.get("tier2_paywall", [])

    # Particionar tier1/tier2 entre implementadas e roadmap
    tier1_impl = [db for db in dbs["tier1"] if db in TIER1_RUNNERS]
    tier1_roadmap = [db for db in dbs["tier1"] if db not in TIER1_RUNNERS]
    tier2_impl = [db for db in dbs["tier2"] if db in TIER1_RUNNERS]
    tier2_roadmap = [db for db in dbs["tier2"] if db not in TIER1_RUNNERS]
    tier2_pw_impl = [db for db in tier2_paywall if db in TIER1_RUNNERS]

    msg = []
    msg.append("=" * 70)
    msg.append("DISCLOSURE — Política OA-first com cascata paywall (v2.15.0)")
    msg.append("=" * 70)
    msg.append(f"Modo: {mode}")
    msg.append(f"Área: {area}")
    msg.append(f"Janela temporal: {year_start} a {year_end}")
    msg.append(f"Query: {query}")
    msg.append("")
    msg.append("BUSCAS QUE VOU EXECUTAR AGORA:")
    msg.append(f"  Tier 1 (OA gratuito, full-text) — {len(tier1_impl)} bases:")
    msg.append(f"    {', '.join(tier1_impl)}")
    msg.append(f"  Tier 2 (metadados livres) — {len(tier2_impl)} bases:")
    msg.append(f"    {', '.join(tier2_impl)}")
    if tier2_pw_impl:
        msg.append(f"  Tier 2 paywall (cascata KEY→PROXY→FALLBACK_MD, DD-8) — "
                   f"{len(tier2_pw_impl)} bases:")
        msg.append(f"    {', '.join(tier2_pw_impl)}")
        msg.append("    Cada uma tenta: chave de API (env var) → proxy institucional →")
        msg.append("    fallback citations_to_obtain_<base>.md com instruções CAFe.")
    msg.append("")

    if tier1_roadmap or tier2_roadmap:
        all_roadmap = tier1_roadmap + tier2_roadmap
        msg.append(f"BASES DECLARADAS NO ROADMAP (sem adapter ainda) — {len(all_roadmap)}:")
        msg.append(f"  {', '.join(all_roadmap)}")
        msg.append(f"  Têm API pública mas adapter dedicado fica para release futura.")
        msg.append(f"  Cobertura parcial via Tier 2 (crossref + openalex + semantic_scholar).")
        msg.append("")

    if unimpl:
        msg.append(f"BASES INVIÁVEIS AUTOMATICAMENTE — {len(unimpl)}:")
        for u in unimpl:
            msg.append(f"  • {u['db']} — {u['reason']}")
        msg.append(f"  Acesso só via Periódicos CAPES com CAFe ou exportação manual.")
        msg.append(f"  Não buscadas; declaradas como gap honestamente.")
        msg.append("")

    if p0:
        msg.append(f"BASES priority_0 (alta relevância, paywall sem adapter) — {len(p0)}:")
        msg.append(f"  {', '.join(p0)}")
        msg.append(f"  Tentativa de acesso em ordem: Unpaywall → OAB → CORE → Periódicos CAPES.")
        msg.append(f"  O que sobrar entra em gap_report.md (Decisão 24).")
        if pol.get("tier3_required") or pol.get("priority_0_required"):
            msg.append(
                "  AVISO: o modo escolhido (SR estrito) requer cobertura ampla destas bases."
            )
            msg.append(
                "  Itens não resolvidos por Tier 0 nem providenciados manualmente serão"
            )
            msg.append("  exclusões por inacessibilidade no PRISMA flow diagram.")
        msg.append("")
    msg.append(
        f"Mínimo Tier 1 para este modo: {pol['tier1_min_databases']} bases buscadas."
    )
    msg.append("=" * 70)
    return "\n".join(msg)


def build_user_disclosure_post(results_summary):
    """Mensagem de transparência APÓS a busca."""
    msg = []
    msg.append("")
    msg.append("=" * 70)
    msg.append("DISCLOSURE — Resultados da busca")
    msg.append("=" * 70)
    msg.append(f"Tier 1 (full-text acessível): {results_summary.get('tier1_total', 0)} estudos")
    msg.append(
        f"Tier 2 (metadados; full-text pode requerer fornecimento): "
        f"{results_summary.get('tier2_total', 0)} estudos"
    )
    msg.append(
        f"Tier 0 routing (priority_0; via Unpaywall/OAB/CORE/Periódicos CAPES + gap report): "
        f"{results_summary.get('tier3_total', 0)} estudos"
    )
    msg.append("")
    msg.append("Para o pacote Zenodo:")
    msg.append("  - studies_with_fulltext_oa.csv → Tier 1")
    msg.append("  - studies_with_metadata_only.csv → Tier 2 sem full-text acessível")
    msg.append("  - studies_via_user_supplied.csv → bases priority_0 fornecidas manualmente")
    msg.append("=" * 70)
    return "\n".join(msg)


def run_tier1_searches(area, query, year_start, year_end, output_dir):
    """Executa scripts Tier 1 disponíveis para a área."""
    dbs = TIER_DATABASES[area]["tier1"]
    return _run_searches_list(dbs, query, year_start, year_end, output_dir, label="Tier 1")


def run_tier2_paywall_searches(area, query, year_start, year_end, output_dir):
    """Executa scripts Tier 2 paywall com cascata KEY→PROXY→FALLBACK_MD (DD-8).

    Cada adapter herda de PaywallAdapter e tenta automaticamente:
    1. Chave de API (env var ou argumento)
    2. Proxy institucional (env var ou argumento)
    3. Fallback citations_to_obtain_<base>.md gerado no output_dir.

    Sem credencial nenhuma, gera apenas o .md (não falha).
    """
    paywall_dbs = TIER_DATABASES[area].get("tier2_paywall", [])
    if not paywall_dbs:
        return {}
    return _run_searches_list(paywall_dbs, query, year_start, year_end, output_dir,
                               label="Tier 2 paywall (cascata)",
                               extra_args=["--output-dir", str(Path(output_dir))])


def _run_searches_list(db_list, query, year_start, year_end, output_dir,
                       label="Tier 1", extra_args=None):
    """Helper genérico para rodar uma lista de adapters.

    v2.17.0 (DD-10): após cada adapter executado com sucesso, chama
    _log_enrichment para gerar logs Camada 1 (fetched/kept/discarded_local) em
    `<output_dir>/logs/logs_<source>.jsonl`.

    F6 (v2.18.1): grey_lit é caso especial — itera por TODOS os 7 providers
    (world_bank, unesco, oecd, ipea, inep, nist, who), não só o default.
    Antes da v2.18.1, orquestrador capturava 1/7 da cobertura sem declarar.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_files = {}
    print(f"\n[{label}] Buscando em {len(db_list)} bases...")

    # Lazy import para evitar import circular
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from _log_enrichment import enrich_log_camada1
    except ImportError:
        enrich_log_camada1 = None

    # F6: providers de grey_lit (lazy import para honrar a fonte de verdade)
    grey_lit_providers = []
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from search_grey_lit import PROVIDERS as _GREY_LIT_PROVIDERS
        grey_lit_providers = list(_GREY_LIT_PROVIDERS.keys())
    except ImportError:
        pass

    for db in db_list:
        runner = TIER1_RUNNERS.get(db)
        if not runner:
            print(
                f"  [skip] {db} — sem runner implementado nesta versão (use Tier 2 fallback)",
                file=sys.stderr,
            )
            continue
        script_path = SCRIPTS_DIR / runner
        if not script_path.exists():
            print(f"  [skip] {db} — script {runner} não encontrado", file=sys.stderr)
            continue

        # F6: caso especial grey_lit — iterar todos os 7 providers
        if db == "grey_lit" and grey_lit_providers:
            for provider in grey_lit_providers:
                provider_db = f"grey_lit_{provider}"
                out_file = output_dir / f"results_{provider_db}.json"
                cmd = [
                    sys.executable, str(script_path),
                    "--query", query,
                    "--provider", provider,
                    "--output", str(out_file),
                ]
                if year_start and year_end:
                    cmd.extend(["--year-start", str(year_start),
                                 "--year-end", str(year_end)])
                if extra_args:
                    cmd.extend(extra_args)
                print(f"  [run]  {provider_db} → {out_file.name}")
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=300)
                    results_files[provider_db] = str(out_file)
                    if enrich_log_camada1 and out_file.exists():
                        try:
                            ys = int(year_start) if year_start else None
                            ye = int(year_end) if year_end else None
                            enrich_log_camada1(out_file, ys, ye)
                        except Exception:
                            pass
                except subprocess.TimeoutExpired:
                    print(f"  [warn] {provider_db} — timeout", file=sys.stderr)
                except subprocess.CalledProcessError as e:
                    print(f"  [warn] {provider_db} — erro: {e.stderr.decode()[:200]}",
                          file=sys.stderr)
            continue

        # Caso padrão (todos exceto grey_lit)
        out_file = output_dir / f"results_{db}.json"
        cmd = [
            sys.executable, str(script_path),
            "--query", query,
            "--output", str(out_file),
        ]
        if year_start and year_end:
            cmd.extend(["--year-start", str(year_start), "--year-end", str(year_end)])
        if extra_args:
            cmd.extend(extra_args)
        print(f"  [run]  {db} → {out_file.name}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
            results_files[db] = str(out_file)
            # DD-10: enrich com logs Camada 1
            if enrich_log_camada1 and out_file.exists():
                try:
                    ys = int(year_start) if year_start else None
                    ye = int(year_end) if year_end else None
                    enrich_log_camada1(out_file, ys, ye)
                except Exception:
                    pass  # não deve falhar a busca por causa de logging
        except subprocess.TimeoutExpired:
            print(f"  [warn] {db} — timeout", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"  [warn] {db} — erro: {e.stderr.decode()[:200]}", file=sys.stderr)
    return results_files


def _collect_dois_from_tier_files(tier_files: list) -> list:
    """Extrai DOIs únicos de arquivos JSON gerados pelos search_*.py.

    Os scripts Tier 1 produzem JSON com campo 'doi' em cada record (quando disponível).
    Tolera múltiplos formatos: {"results": [{"doi": ...}]} ou [{"doi": ...}, ...].
    """
    seen = set()
    dois = []
    for f in tier_files or []:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        records = data if isinstance(data, list) else (
            data.get("results") or data.get("records") or data.get("hits") or []
        )
        if not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            doi = rec.get("doi") or rec.get("DOI") or (rec.get("identifier") or {}).get("doi")
            if doi and isinstance(doi, str):
                doi_norm = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
                if doi_norm and "/" in doi_norm and doi_norm not in seen:
                    seen.add(doi_norm)
                    dois.append(doi_norm)
    return dois


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Query de busca")
    parser.add_argument("--year-start", required=True, help="Ano inicial (e.g., 2020)")
    parser.add_argument("--year-end", required=True, help="Ano final (e.g., 2026)")
    parser.add_argument(
        "--area", choices=list(TIER_DATABASES.keys()), required=True,
        help="Área: saude | educacao | cs_se | multi",
    )
    parser.add_argument(
        "--mode", choices=list(MODE_TIER_POLICY.keys()), required=True,
        help="Modo de revisão",
    )
    parser.add_argument(
        "--output-dir", default="search_results",
        help="Diretório de saída para os resultados",
    )
    parser.add_argument(
        "--user-supplied-tier3", default=None,
        help="Caminho para CSV/RIS de bases priority_0 (Scopus/WoS/etc.) exportado pelo usuário",
    )
    parser.add_argument(
        "--skip-tier0", action="store_true",
        help="Desliga o enriquecimento Tier 0 (Unpaywall + Open Access Button). "
             "Use apenas em modo offline/CI; em uso normal Tier 0 roda sempre.",
    )
    parser.add_argument(
        "--contact-email", default=None,
        help="Email de contato para APIs (Unpaywall exige). Lê IGNORANTIA_CONTACT_EMAIL "
             "do ambiente se não passado. Se ausente em ambos, Tier 0 emite warning e segue.",
    )
    parser.add_argument(
        "--project-id", default="(não nomeado)",
        help="Identificador legível do projeto, usado no cabeçalho do gap_report.md.",
    )
    parser.add_argument(
        "--resume-after-gap-report", action="store_true",
        help="Retoma execução após usuário ter providenciado full-texts no diretório "
             "user_provided/ em resposta ao gap_report.md gerado em execução anterior.",
    )
    parser.add_argument(
        "--skip-gap-resolution", action="store_true",
        help="Pula a etapa de pausa para resolução de gap. Itens inacessíveis serão "
             "registrados como excluídos por inacessibilidade no PRISMA flow diagram.",
    )
    args = parser.parse_args()

    # D6 (v2.23.0, auditoria #5): capturar timestamp inicial para
    # orchestration_summary.json com started_at/finished_at.
    _started_at = datetime.now(timezone.utc).isoformat() + "Z"

    # Resolver email de contato: argumento > env var > None (com warning)
    contact_email = args.contact_email or os.environ.get("IGNORANTIA_CONTACT_EMAIL")

    # Validação de combinação modo/área
    pol = MODE_TIER_POLICY[args.mode]

    # Disclosure ao usuário ANTES
    print(build_user_disclosure_pre(args.area, args.mode, args.year_start, args.year_end, args.query))
    print()

    # Tier 1 — sempre, primeiro
    print("[Tier 1] Buscando em bases OA gratuitas...")
    tier1_files = run_tier1_searches(
        args.area, args.query, args.year_start, args.year_end, args.output_dir
    )

    # Tier 2 — recomendado mas opcional para alguns modos
    print("\n[Tier 2] Tier 2 implementado nos scripts existentes (search_crossref.py, search_semantic_scholar.py)")
    print("        — execute-os separadamente se desejar enriquecer Tier 1.")

    # Tier 2 paywall (v2.15.0) — cascata KEY → PROXY → FALLBACK_MD (DD-8)
    paywall_files = run_tier2_paywall_searches(
        args.area, args.query, args.year_start, args.year_end, args.output_dir
    )

    # Decisão 22 (v2.9.0/v2.10.1): registrar search_run no manifest
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from manifest_helpers import (load_manifest, save_manifest,
                                       record_search_run as _record_search_run)
        manifest_path = Path(args.output_dir) / "reproducibility_manifest.yaml"
        manifest = load_manifest(manifest_path)
        manifest = _record_search_run(
            manifest,
            query=args.query, area=args.area,
            year_start=int(args.year_start), year_end=int(args.year_end),
            databases_searched=list(tier1_files.keys()) if isinstance(tier1_files, dict) else [],
        )
        save_manifest(manifest, manifest_path)
        print(f"\n[manifest] search_run registrada em {manifest_path}")
    except Exception as exc:
        print(f"\n[manifest] [warn] não foi possível registrar search_run: {exc}",
              file=sys.stderr)

    # Bases priority_0 — só via fornecimento do usuário (após Tier 0 routing falhar)
    tier3_summary = {"count": 0, "source": None}
    if args.user_supplied_tier3:
        path = Path(args.user_supplied_tier3)
        if path.exists():
            print(f"\n[priority_0] Material fornecido pelo usuário: {path}")
            # Conta linhas (heurística simples)
            try:
                with open(path) as f:
                    n = sum(1 for _ in f) - 1  # subtract header
                tier3_summary = {"count": max(0, n), "source": str(path)}
                print(f"  ~{tier3_summary['count']} registros fornecidos")
            except Exception as e:
                print(f"  [warn] não consegui ler: {e}")
    elif pol["tier3_required"]:
        print("\n[priority_0] AVISO: este modo (SR estrito) requer cobertura priority_0 ampla.\n"
              "         Itens não resolvidos por Tier 0 nem providenciados manualmente\n"
              "         viram exclusões por inacessibilidade no PRISMA flow diagram.")
        print("        Forneça --user-supplied-tier3 com export de Scopus/WoS.")

    # Tier 0 — enriquecimento OA legítimo, AUTOMÁTICO (Decisão 17, v2.6.1)
    # Se é legal, é feito. Não há flag de opt-in.
    tier0_summary = {"executed": False, "skipped": False, "n_dois": 0, "n_oa_found": 0,
                     "n_author_request_only": 0, "method": None}
    if args.skip_tier0:
        print("\n[Tier 0] PULADO via --skip-tier0 (modo offline/CI).")
        tier0_summary["skipped"] = True
    else:
        print("\n[Tier 0] Resolvendo DOIs para URLs OA legítimas (Unpaywall + Open Access Button)...")
        print("         Decisão 17: apenas fontes OA licenciadas. Plataformas em disputa judicial excluídas.")
        if not contact_email:
            print("         [warn] sem email de contato (--contact-email ou IGNORANTIA_CONTACT_EMAIL).")
            print("                Unpaywall exige email; resolução pode falhar.")
            print("                Documentação: https://unpaywall.org/products/api")
        from tier0_resolver import resolve_dois_with_tier0  # noqa: E402
        collected_dois = _collect_dois_from_tier_files(tier1_files)
        if collected_dois:
            tier0_records = resolve_dois_with_tier0(
                collected_dois,
                email=contact_email or "",
                mock=False,  # produção real; CI usa --skip-tier0
            )
            tier0_path = Path(args.output_dir) / "tier0_oa_enrichment.json"
            tier0_payload = {
                "schema_version": "1.0.0",
                "tier": 0,
                "n_dois": len(tier0_records),
                "n_oa_found": sum(1 for r in tier0_records if r.has_legitimate_oa),
                "n_author_request_only": sum(
                    1 for r in tier0_records
                    if not r.has_legitimate_oa and r.request_url_for_author
                ),
                "records": [r.__dict__ for r in tier0_records],
            }
            with open(tier0_path, "w", encoding="utf-8") as f:
                json.dump(tier0_payload, f, indent=2, ensure_ascii=False)
            tier0_summary = {
                "executed": True,
                "skipped": False,
                "n_dois": tier0_payload["n_dois"],
                "n_oa_found": tier0_payload["n_oa_found"],
                "n_author_request_only": tier0_payload["n_author_request_only"],
                "method": "UNPAYWALL+OAB",
                "output": str(tier0_path),
            }
            print(f"         {tier0_summary['n_oa_found']}/{tier0_summary['n_dois']} "
                  f"DOIs com OA legítimo; {tier0_summary['n_author_request_only']} "
                  f"requerem solicitação ao autor.")
            print(f"         Resultado: {tier0_path}")
        else:
            tier0_summary["executed"] = True
            print("         [info] nenhum DOI coletado dos Tiers 1 — nada a resolver.")

    # Gap Report — relatório de itens inacessíveis (v2.7.0, posição neutra)
    # Linguagem deliberadamente neutra: o skill declara o gap; usuário decide o que fazer.
    gap_report_summary = {"generated": False, "n_items": 0, "path": None,
                          "paused_for_user": False}
    user_provided_dir = Path(args.output_dir) / "user_provided"
    user_provided_dir.mkdir(parents=True, exist_ok=True)

    if args.resume_after_gap_report:
        # Retomada: contar arquivos providenciados pelo usuário e continuar
        provided_files = list(user_provided_dir.glob("*"))
        gap_report_summary["resumed"] = True
        gap_report_summary["n_provided_by_user"] = len(provided_files)
        print(f"\n[Gap Report] RETOMADA após resolução manual.")
        print(f"             {len(provided_files)} arquivo(s) encontrado(s) em {user_provided_dir}")
    elif args.skip_gap_resolution:
        gap_report_summary["skipped"] = True
        print("\n[Gap Report] PULADO via --skip-gap-resolution.")
        print("             Itens inacessíveis serão excluídos por inacessibilidade no PRISMA.")
    elif tier0_summary.get("executed") and tier0_summary.get("output"):
        # Caminho normal: gera relatório e pausa
        try:
            from access_gap_report import generate_gap_report  # noqa: E402
            with open(tier0_summary["output"], encoding="utf-8") as f:
                tier0_payload_full = json.load(f)
            gap_report_path = Path(args.output_dir) / "gap_report.md"
            report = generate_gap_report(
                tier0_payload_full,
                output_path=gap_report_path,
                project_id=args.project_id,
                input_dir=str(user_provided_dir),
            )
            gap_report_summary = {
                "generated": True,
                "n_items": report.n_items,
                "n_articles": report.n_articles,
                "n_books": report.n_books,
                "n_other": report.n_other,
                "path": str(gap_report_path),
                "paused_for_user": report.n_items > 0,
            }
            print(f"\n[Gap Report] {report.n_items} item(ns) com acesso pendente "
                  f"({report.n_articles} artigos, {report.n_books} livros/capítulos, "
                  f"{report.n_other} outros).")
            print(f"             Relatório: {gap_report_path}")
            if report.n_items > 0:
                print(f"             Coloque full-texts em: {user_provided_dir}")
                print()
                print("             ⏸  PAUSA: revise o relatório e providencie os itens necessários.")
                print("                Como você obtém os itens é decisão sua. O `ignorantia` não")
                print("                recomenda nem desaconselha plataformas, serviços ou métodos.")
                print()
                print("                Quando estiver pronto, retome com:")
                print(f"                   --resume-after-gap-report --output-dir {args.output_dir}")
                print()
                print("                Para prosseguir agora sem providenciar nenhum item adicional:")
                print(f"                   --skip-gap-resolution --output-dir {args.output_dir}")
        except ImportError as exc:
            print(f"\n[Gap Report] [warn] não consegui importar access_gap_report: {exc}",
                  file=sys.stderr)

    # Resultados
    summary = {
        "tier0": tier0_summary,
        "gap_report": gap_report_summary,
        "tier1_files": tier1_files,
        "tier1_total_databases_searched": len(tier1_files),
        "tier2_total": 0,  # preenchido após executar scripts Tier 2 separadamente
        "tier3_total": tier3_summary["count"],
        "tier3_source": tier3_summary["source"],
        "compliance": {
            "tier1_min_required": pol["tier1_min_databases"],
            "tier1_min_satisfied": len(tier1_files) >= pol["tier1_min_databases"],
            "tier3_required_by_mode": pol["tier3_required"],
            "tier3_provided": tier3_summary["source"] is not None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }
    # search_summary.json é o nome legado; mantido para retrocompat.
    legacy_summary_path = Path(args.output_dir) / "search_summary.json"
    with open(legacy_summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # D6 (v2.23.0, auditoria #5): orchestration_summary.json é o nome canônico
    # com campos extras (started_at, finished_at, adapters_run, sandbox_warnings).
    # Nome legado search_summary.json mantido como alias para retrocompat.
    orch_summary = {
        **summary,
        "started_at": _started_at,
        "finished_at": datetime.now(timezone.utc).isoformat() + "Z",
        "adapters_run": [Path(p).stem.replace("results_", "")
                          for p in tier1_files],
        "schema_version": "1.0.0",
    }
    orch_summary_path = Path(args.output_dir) / "orchestration_summary.json"
    with open(orch_summary_path, "w") as f:
        json.dump(orch_summary, f, indent=2, ensure_ascii=False)
    print(f"\n[Resumo] {orch_summary_path}")

    # Pausa para resolução de gap, se aplicável
    if gap_report_summary.get("paused_for_user"):
        print("\n[Status] EM PAUSA aguardando providenciamento manual de full-texts.")
        print(f"         Exit code 10 indica pausa intencional (não é erro).")
        sys.exit(10)

    # Disclosure ao usuário APÓS
    print(build_user_disclosure_post({
        "tier1_total": len(tier1_files),
        "tier2_total": 0,
        "tier3_total": tier3_summary["count"],
    }))

    # Compliance check
    if not summary["compliance"]["tier1_min_satisfied"]:
        print(
            f"\n⚠️  ALERTA: Modo {args.mode} requer mínimo "
            f"{pol['tier1_min_databases']} bases Tier 1, mas "
            f"{len(tier1_files)} foram efetivamente buscadas.",
            file=sys.stderr,
        )
        sys.exit(2)

    if pol["tier3_required"] and not summary["compliance"]["tier3_provided"]:
        print(
            f"\n⚠️  ALERTA: Modo {args.mode} (SR estrito) requer cobertura priority_0 ampla "
            f"via fornecimento do usuário. Sem isso, o manuscrito pode não atender "
            f"venues Q1 de SR estrito.",
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
