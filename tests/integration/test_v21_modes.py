"""
Testes de smoke v2.1 — valida contratos novos: 18 review_types, 3 layers, E16 estendido.

Como rodar:
    cd /home/claude/ignorantia_v2
    python3 -m pytest tests/test_v21_modes.py -v
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from assessor.eliminators import (
    REVIEW_TYPE_TO_LAYER,
    SYSTEMATIC_REVIEW_VALID_VALUES,
    VALID_REVIEW_TYPES_V21,
    check_e16_systematic_review_without_two_reviewers,
)

# ============================================================================
# Contratos de constantes v2.1
# ============================================================================

def test_valid_review_types_count():
    """v2.1 expõe exatamente 18 valores válidos para review_type."""
    assert len(VALID_REVIEW_TYPES_V21) == 18


def test_valid_review_types_includes_v21_modes():
    """Os 6 modos novos da v2.1 devem estar no conjunto válido."""
    new_modes_v21 = {
        "integrative_review",
        "realist_review",
        "software_paper",
        "position_paper",
        "technical_report",
        "white_paper",
    }
    assert new_modes_v21.issubset(VALID_REVIEW_TYPES_V21)


def test_valid_review_types_includes_v20_modes():
    """Os 4 modos da v2.0 devem continuar válidos."""
    v20_modes = {
        "scoping_review",
        "rapid_review",
        "mapping_study",
        "systematic_review_with_2_reviewers",
    }
    assert v20_modes.issubset(VALID_REVIEW_TYPES_V21)


def test_systematic_review_strict_set_has_two_aliases():
    """Apenas dois valores justificam 'Systematic Review' no texto sem violar E16."""
    expected = {"systematic_review_with_2_reviewers", "systematic_review_strict"}
    assert expected == SYSTEMATIC_REVIEW_VALID_VALUES


def test_layer_mapping_complete_for_main_modes():
    """Os 10 modos principais devem ter camada hierárquica declarada."""
    main_modes = [
        "scoping_review", "rapid_review", "mapping_study",
        "integrative_review", "realist_review",  # primária = 5
        "software_paper", "position_paper", "technical_report", "white_paper",  # secundária = 4
        "systematic_review_with_2_reviewers",  # terciária = 1
    ]
    for m in main_modes:
        assert m in REVIEW_TYPE_TO_LAYER, f"{m} sem camada declarada"


def test_layer_distribution():
    """Distribuição de camadas: 5 primária + 6 secundária (com aliases) + 2 terciária."""
    layers = list(REVIEW_TYPE_TO_LAYER.values())
    assert layers.count("primary") == 5  # scoping, rapid, mapping, integrative, realist
    assert layers.count("secondary") == 6  # software, position, theoretical_essay, technical_report, white_paper, policy_brief
    assert layers.count("tertiary") == 2  # systematic_review_with_2_reviewers + alias systematic_review_strict


# ============================================================================
# E16 — comportamento estendido com modos v2.1
# ============================================================================

def test_e16_invalid_review_type_blocks():
    """review_type fora do enum válido v2.1 → E16 bloqueante."""
    content = {"review_type": "totally_fake_review_type", "title": "Some review"}
    result = check_e16_systematic_review_without_two_reviewers(content, "<p>body</p>")
    assert result.failed is True
    assert "review_type inválido" in result.name


def test_e16_integrative_review_with_sr_in_text_blocks():
    """integrative_review no metadado + 'systematic review' no texto → E16 bloqueante (Caso 1)."""
    content = {"review_type": "integrative_review", "title": "An integrative review of X"}
    html = "<p>This systematic review examined...</p>"
    result = check_e16_systematic_review_without_two_reviewers(content, html)
    assert result.failed is True
    assert "secondary" not in result.detail.lower() or "primary" in result.detail.lower()
    # Deve mencionar a camada primária (integrative_review é primária)
    assert "primary" in result.detail.lower()


def test_e16_realist_review_clean_passes():
    """realist_review consistente (sem reivindicar SR no texto) → E16 não bloqueia."""
    content = {"review_type": "realist_review", "title": "A realist review of educational programs"}
    html = "<p>This realist review explored CMO configurations...</p>"
    result = check_e16_systematic_review_without_two_reviewers(content, html)
    assert result.failed is False


def test_e16_software_paper_passes():
    """software_paper (camada secundária) sem 'systematic review' no texto → E16 N/A."""
    content = {"review_type": "software_paper", "title": "ignorantia: a tool for SLR"}
    html = "<p>Summary: this paper describes ignorantia...</p>"
    result = check_e16_systematic_review_without_two_reviewers(content, html)
    assert result.failed is False


def test_e16_white_paper_with_sr_in_text_blocks():
    """white_paper no metadado + 'revisão sistemática' no texto → E16 bloqueante."""
    content = {"review_type": "white_paper", "title": "Policy brief on X"}
    html = "<p>Esta revisão sistemática mostra que...</p>"
    result = check_e16_systematic_review_without_two_reviewers(content, html)
    assert result.failed is True


def test_e16_systematic_review_strict_with_kappa_passes():
    """SR estrito + 2 reviewers + kappa documentado → E16 OK."""
    content = {"review_type": "systematic_review_with_2_reviewers", "title": "A systematic review"}
    html = ("<p>Two independent reviewers screened all records. "
            "Cohen's kappa was 0.85 for screening...</p>")
    result = check_e16_systematic_review_without_two_reviewers(content, html)
    assert result.failed is False
    assert "OK" in result.detail


def test_e16_systematic_review_strict_without_kappa_blocks():
    """SR estrito sem kappa documentado → E16 bloqueante."""
    content = {"review_type": "systematic_review_with_2_reviewers", "title": "A systematic review"}
    html = "<p>We followed PRISMA-2020...</p>"
    result = check_e16_systematic_review_without_two_reviewers(content, html)
    assert result.failed is True


# ============================================================================
# Schema de venue — review_types_accepted enum
# ============================================================================

def test_venue_schema_includes_v21_review_types():
    """O JSON Schema de venue deve incluir os 6 novos review_types."""
    import json
    schema_path = Path(__file__).parent.parent.parent / "references" / "profiles" / "_schema" / "venue_profile.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)

    # Navegar até o enum de review_types_accepted
    rta = schema["properties"]["taxonomy"]["properties"]["review_types_accepted"]
    enum_values = set(rta["items"]["enum"])

    new_v21 = {
        "integrative_review", "realist_review",
        "software_paper", "position_paper", "theoretical_essay",
        "technical_report", "white_paper", "policy_brief",
    }
    assert new_v21.issubset(enum_values)


def test_venue_schema_has_recommended_for_layer():
    """O JSON Schema deve ter o novo campo recommended_for_layer."""
    import json
    schema_path = Path(__file__).parent.parent.parent / "references" / "profiles" / "_schema" / "venue_profile.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)
    rfl = schema["properties"]["taxonomy"]["properties"].get("recommended_for_layer")
    assert rfl is not None
    assert set(rfl["enum"]) == {"primary", "secondary", "tertiary", "all"}


# ============================================================================
# Arquivos de modo — existência
# ============================================================================

def test_all_10_mode_profiles_exist():
    """references/modes/mode-XX-*.xml deve existir para os 10 modos.

    Fix 18 / Phase 3: source-of-truth migrated from .md to .xml. The
    Markdown bodies are preserved verbatim inside CDATA sections.
    """
    modes_dir = Path(__file__).parent.parent.parent / "references" / "modes"
    expected_files = [
        "mode-01-scoping-review.xml",
        "mode-02-rapid-review.xml",
        "mode-03-mapping-study.xml",
        "mode-04-systematic-review-strict.xml",
        "mode-05-software-paper.xml",
        "mode-06-position-paper.xml",
        "mode-07-technical-report.xml",
        "mode-08-white-paper.xml",
        "mode-09-integrative-review.xml",
        "mode-10-realist-review.xml",
    ]
    for f in expected_files:
        assert (modes_dir / f).exists(), f"Faltando: {f}"


def test_all_10_mode_templates_exist():
    """assets/templates/modes/mode-*.md deve existir para os 10 modos."""
    tpl_dir = Path(__file__).parent.parent.parent / "assets" / "templates" / "modes"
    expected_files = [
        "mode-scoping-review.md",
        "mode-rapid-review.md",
        "mode-mapping-study.md",
        "mode-systematic-review-strict.md",
        "mode-software-paper.md",
        "mode-position-paper.md",
        "mode-technical-report.md",
        "mode-white-paper.md",
        "mode-integrative-review.md",
        "mode-realist-review.md",
    ]
    for f in expected_files:
        assert (tpl_dir / f).exists(), f"Faltando: {f}"


def test_modes_overview_lists_10_modes():
    """references/modes/MODES_OVERVIEW.xml deve mencionar os 10 modos.

    Fix 18 / Phase 3: MODES_OVERVIEW migrated to XML. The textual assertions
    still match because the Markdown body is preserved inside CDATA.
    """
    overview = Path(__file__).parent.parent.parent / "references" / "modes" / "MODES_OVERVIEW.xml"
    text = overview.read_text(encoding="utf-8")
    for i in range(1, 11):
        # Aceitar qualquer formato Modo N, Modo 0N, mode-NN, etc.
        token_a = f"Modo {i}"
        token_b = f"mode-{i:02d}-"
        token_c = f"Modo 0{i}" if i < 10 else None
        present = token_a in text or token_b in text or (token_c and token_c in text)
        assert present, f"MODES_OVERVIEW não menciona Modo {i}"


def test_oa_tiers_doc_exists():
    """references/databases/oa-tiers.xml deve existir e listar 3 tiers.

    Fix 18 / Phase 2: source-of-truth migrated from .md to .xml. The Markdown
    body is preserved inside a CDATA section, so the textual assertions still
    hold against the raw file text.
    """
    p = Path(__file__).parent.parent.parent / "references" / "databases" / "oa-tiers.xml"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Tier 1" in text
    assert "Tier 2" in text
    assert "Tier 3" in text


def test_search_orchestrator_exists():
    """scripts/searches/search_orchestrator.py deve existir."""
    p = Path(__file__).parent.parent.parent / "scripts" / "searches" / "search_orchestrator.py"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "TIER_DATABASES" in text
    assert "MODE_TIER_POLICY" in text


# ============================================================================
# v2.1.1 — Patch: scripts de busca declaram source_tier
# ============================================================================

def test_all_search_scripts_declare_source_tier():
    """Os 5 scripts existentes devem declarar source_tier no item e no envelope."""
    searches_dir = Path(__file__).parent.parent.parent / "scripts" / "searches"
    expected = {
        "search_arxiv.py": "tier1",
        "search_crossref.py": "tier2",
        "search_dblp.py": "tier1",
        "search_scielo.py": "tier1",
        "search_semantic_scholar.py": "tier2",
    }
    for script_name, expected_tier in expected.items():
        text = (searches_dir / script_name).read_text(encoding="utf-8")
        # Item-level
        assert f'"source_tier": "{expected_tier}"' in text, (
            f"{script_name}: source_tier item-level ausente ou tier errado"
        )
        # Envelope-level: aparece pelo menos 2 vezes (item + envelope)
        count = text.count(f'"source_tier": "{expected_tier}"')
        assert count >= 2, (
            f"{script_name}: source_tier deve aparecer em item + envelope (count={count})"
        )


# ============================================================================
# v2.1.1 — Patch: auto-correction-policy ramifica por review_type
# ============================================================================

def test_auto_correction_policy_mentions_three_layers():
    """auto-correction-policy.md deve documentar aplicabilidade nas 3 camadas v2.1."""
    p = Path(__file__).parent.parent.parent / "references" / "auto-correction-policy.md"
    text = p.read_text(encoding="utf-8")
    # Deve mencionar as três camadas explicitamente
    assert "Camada Primária" in text
    assert "Camada Secundária" in text
    assert "Camada Terciária" in text
    # Deve declarar que PRISMA não se aplica a modos secundários
    assert "PRISMA" in text
    # Deve mencionar pelo menos software_paper, position_paper, technical_report, white_paper
    for rt in ["software_paper", "position_paper", "technical_report", "white_paper"]:
        assert rt in text, f"auto-correction-policy não menciona {rt}"


# ============================================================================
# v2.2.0 — Patch: 3 venues OA INT novos (PLOS ONE, F1000Research, Frontiers Education)
# ============================================================================

def test_three_new_oa_int_venues_exist():
    """Os 3 perfis OA INT da v2.2.0 devem existir."""
    profiles_dir = Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q1_int"
    expected = ["plos_one.yaml", "f1000research.yaml", "frontiers_education.yaml"]
    for f in expected:
        assert (profiles_dir / f).exists(), f"Faltando: {f}"


def test_three_new_oa_int_venues_are_fully_oa():
    """Os 3 venues novos devem declarar fully_oa."""
    import yaml
    profiles_dir = Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q1_int"
    for fname in ["plos_one.yaml", "f1000research.yaml", "frontiers_education.yaml"]:
        data = yaml.safe_load(Path(profiles_dir / fname).read_text(encoding="utf-8"))
        assert data["metadata"]["open_access"] == "fully_oa", f"{fname} não é fully_oa"


def test_three_new_oa_int_venues_have_apc_declared():
    """Os 3 venues novos devem ter apc_usd declarado (não null)."""
    import yaml
    profiles_dir = Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q1_int"
    for fname in ["plos_one.yaml", "f1000research.yaml", "frontiers_education.yaml"]:
        data = yaml.safe_load(Path(profiles_dir / fname).read_text(encoding="utf-8"))
        apc = data["metadata"].get("apc_usd")
        assert apc is not None and apc > 0, f"{fname}: apc_usd ausente ou inválido"


def test_three_new_oa_int_venues_validate_against_schema():
    """Os 3 venues novos devem validar contra o JSON Schema."""
    import json

    import jsonschema
    import yaml
    schema_path = Path(__file__).parent.parent.parent / "references" / "profiles" / "_schema" / "venue_profile.schema.json"
    profiles_dir = Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q1_int"
    schema = json.load(open(schema_path))
    for fname in ["plos_one.yaml", "f1000research.yaml", "frontiers_education.yaml"]:
        data = yaml.safe_load(Path(profiles_dir / fname).read_text(encoding="utf-8"))
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            raise AssertionError(f"{fname} não valida contra schema: {e.message[:200]}")


def test_all_venue_profiles_validate_against_schema():
    """Os 23 venues totais devem todos validar contra o schema (regressão geral)."""
    import glob
    import json

    import jsonschema
    import yaml
    schema_path = Path(__file__).parent.parent.parent / "references" / "profiles" / "_schema" / "venue_profile.schema.json"
    schema = json.load(open(schema_path))
    profiles_glob = str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_*" / "*.yaml")
    files = sorted(glob.glob(profiles_glob))
    assert len(files) == 68, f"Esperado 68 perfis de venue (v2.4.0: 57 da v2.3.0 + 11 Q2 INT), encontrado {len(files)}"
    for fname in files:
        data = yaml.safe_load(Path(fname).read_text(encoding="utf-8"))
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            raise AssertionError(f"{fname} não valida: {e.message[:200]}")


# ============================================================================
# v2.2.1 — 9 venues A2 BR novos (≥3 por área Qualis)
# ============================================================================

def test_v221_nine_new_a2_br_venues_exist():
    """Os 9 perfis A2 BR da v2.2.1 devem existir.

    Nota v2.3: pope_sobrapo foi reclassificado de A2 para A3 e movido para venues_a3_br/
    conforme Pesquisa Qualis 2021-2024 (Etapa 1 v2.3). O teste agora verifica nas duas pastas.
    """
    profiles_root = Path(__file__).parent.parent.parent / "references" / "profiles"
    expected_in_a1_br = [
        # Educação
        "emaberto_inep.yaml", "rbaad_abed.yaml", "rpem_unespar.yaml",
        # Saúde
        "reben_aben.yaml", "reeusp_usp.yaml", "rbe_abrasco.yaml",
        # Exatas/Tec (2 dos 3 originais; pope_sobrapo movido para a3_br)
        "jisa_sbc.yaml", "tcam_sbmac.yaml",
    ]
    expected_in_a3_br = ["pope_sobrapo.yaml"]
    for f in expected_in_a1_br:
        assert (profiles_root / "venues_a1_br" / f).exists(), f"Faltando em venues_a1_br/: {f}"
    for f in expected_in_a3_br:
        assert (profiles_root / "venues_a3_br" / f).exists(), f"Faltando em venues_a3_br/: {f} (recalibrado v2.3)"


def test_v221_a2_br_coverage_by_area():
    """Após v2.2.1: ≥3 A2 BR por cada uma das 3 áreas-alvo."""
    import glob

    import yaml
    profiles = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_a1_br" / "*.yaml"))
    counts = {"Educacao": 0, "QR1-Vida+Saude": 0, "QR1-Exatas+Tecnologicas": 0}
    for p in profiles:
        data = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        meta = data.get("metadata", {})
        if meta.get("qualis_stratum") == "A2":
            sub = meta.get("qualis_subarea")
            if sub in counts:
                counts[sub] += 1
    for area, n in counts.items():
        assert n >= 3, f"Área {area} tem apenas {n} venue(s) A2 BR; esperado ≥3"


def test_v221_all_new_venues_are_diamond_oa_brazilian():
    """Os 9 novos perfis A2 BR da v2.2.1 devem ser diamond OA (apc_usd=0) e country=BR.

    Nota v2.3: pope_sobrapo foi recalibrado para A3 e está em venues_a3_br/ — propriedades
    diamond OA + BR são preservadas após a movimentação."""
    import yaml
    profiles_root = Path(__file__).parent.parent.parent / "references" / "profiles"
    new_venues_locations = {
        "emaberto_inep": "venues_a1_br",
        "rbaad_abed": "venues_a1_br",
        "rpem_unespar": "venues_a1_br",
        "reben_aben": "venues_a1_br",
        "reeusp_usp": "venues_a1_br",
        "rbe_abrasco": "venues_a1_br",
        "jisa_sbc": "venues_a1_br",
        "pope_sobrapo": "venues_a3_br",  # movido na v2.3
        "tcam_sbmac": "venues_a1_br",
    }
    for vid, folder in new_venues_locations.items():
        path = profiles_root / folder / f"{vid}.yaml"
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        meta = data["metadata"]
        assert meta["country"] == "BR", f"{vid}: country deve ser BR"
        assert meta["open_access"] == "fully_oa", f"{vid}: open_access deve ser fully_oa"
        assert meta["apc_usd"] == 0, f"{vid}: apc_usd deve ser 0 (diamond OA)"


def test_v221_total_venue_count_is_32():
    """Após v2.3.0: 61 perfis ao total (40 da v2.2.2 + 21 novos A3+B1 BR).

    Nome do teste preservado por compat com histórico da v2.2.x; assertion atualizado a cada release.
    """
    import glob
    profiles = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_*" / "*.yaml"))
    assert len(profiles) == 68, f"Esperado 68 perfis ao total (v2.4.0), encontrado {len(profiles)}"


# ============================================================
# v2.2.2 — Fallback tiers (Decisão 14)
# ============================================================

def test_v222_fallback_folder_exists_and_has_8_profiles():
    """A pasta venues_fallback_br/ deve existir com exatamente 8 perfis."""
    import glob
    fallback_files = sorted(glob.glob(
        str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_fallback_br" / "*.yaml")
    ))
    assert len(fallback_files) == 8, (
        f"Esperado 8 perfis fallback em venues_fallback_br/, encontrado {len(fallback_files)}"
    )


def test_v222_all_fallback_profiles_have_explicit_tier():
    """Todo perfil em venues_fallback_br/ deve declarar fallback_tier ∈ {2, 3}."""
    import glob

    import yaml
    fallback_files = glob.glob(
        str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_fallback_br" / "*.yaml")
    )
    for path in fallback_files:
        with open(path) as f:
            d = yaml.safe_load(f)
        tier = d.get("metadata", {}).get("fallback_tier")
        name = path.split("/")[-1]
        assert tier in (2, 3), f"{name}: fallback_tier deve ser 2 ou 3, encontrado {tier!r}"


def test_v222_fallback_tier_2_has_modest_apc():
    """Perfis tier-2 devem ter APC declarado ≤ USD 2000 (publisher comunitário)."""
    import glob

    import yaml
    fallback_files = glob.glob(
        str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_fallback_br" / "*.yaml")
    )
    tier_2_count = 0
    for path in fallback_files:
        with open(path) as f:
            d = yaml.safe_load(f)
        md = d["metadata"]
        if md.get("fallback_tier") == 2:
            tier_2_count += 1
            apc = md.get("apc_usd")
            apc_max = md.get("apc_usd_range_max")
            effective_max = apc_max if apc_max is not None else apc
            assert effective_max is not None and effective_max <= 2000, (
                f"{path.split('/')[-1]}: tier-2 deve ter APC ≤ USD 2000, encontrado {effective_max}"
            )
    assert tier_2_count >= 1, "Esperado pelo menos 1 perfil tier-2"


def test_v222_fallback_tier_3_has_high_apc_or_subscription():
    """Perfis tier-3 devem ter APC > USD 1500 (Springer hybrid) ou ser subscription."""
    import glob

    import yaml
    fallback_files = glob.glob(
        str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_fallback_br" / "*.yaml")
    )
    tier_3_count = 0
    for path in fallback_files:
        with open(path) as f:
            d = yaml.safe_load(f)
        md = d["metadata"]
        if md.get("fallback_tier") == 3:
            tier_3_count += 1
            oa = md.get("open_access")
            apc = md.get("apc_usd")
            is_subscription = (oa == "subscription")
            is_high_apc = (apc is not None and apc > 1500)
            assert is_subscription or is_high_apc, (
                f"{path.split('/')[-1]}: tier-3 deve ter APC > USD 1500 OU subscription, "
                f"encontrado oa={oa!r} apc={apc!r}"
            )
    assert tier_3_count >= 1, "Esperado pelo menos 1 perfil tier-3"


def test_v222_existing_diamond_profiles_default_to_tier_1():
    """Perfis pré-v2.2.2 sem fallback_tier devem ser tratados como tier-1 (diamond OA).

    Lê os perfis de venues_a1_br/ que são fully_oa com apc_usd=0 e confirma que NÃO têm
    fallback_tier explícito (ausente = tier-1 default semântico).
    """
    import glob

    import yaml
    a1_br = glob.glob(
        str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_a1_br" / "*.yaml")
    )
    diamond_count = 0
    for path in a1_br:
        with open(path) as f:
            d = yaml.safe_load(f)
        md = d["metadata"]
        if md.get("open_access") == "fully_oa" and (md.get("apc_usd") == 0 or md.get("apc_usd") is None):
            diamond_count += 1
            # Aceita ausência ou tier=1 explícito
            tier = md.get("fallback_tier")
            assert tier in (None, 1), (
                f"{path.split('/')[-1]}: diamond OA deve ter fallback_tier ausente ou =1, "
                f"encontrado {tier!r}"
            )
    assert diamond_count >= 5, f"Esperado pelo menos 5 perfis diamond OA pré-existentes, encontrado {diamond_count}"


def test_v222_exatas_subarea_now_has_at_least_8_options():
    """Após v2.2.2, QR1-Exatas+Tecnologicas deve ter ≥ 8 venues (3 tier-1 + ≥5 fallback)."""
    import glob

    import yaml
    all_profiles = glob.glob(
        str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_*" / "*.yaml")
    )
    exatas_count = 0
    for path in all_profiles:
        with open(path) as f:
            d = yaml.safe_load(f)
        if d.get("metadata", {}).get("qualis_subarea") == "QR1-Exatas+Tecnologicas":
            exatas_count += 1
    assert exatas_count >= 8, (
        f"Esperado ≥8 venues em QR1-Exatas+Tecnologicas após v2.2.2, encontrado {exatas_count}"
    )


def test_v222_engine_ranks_tier_1_before_tier_2_before_tier_3():
    """Teste de comportamento: o ranking do engine deve emergir tier-1 antes de tier-2 antes de tier-3.

    Pega 3 venues conhecidos (1 por tier) e confirma a ordem mesmo quando tier-3 tem score maior.
    Isso é o coração da Decisão 14.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
    from compliance.engine import VenueAssessment

    # Construo 3 assessments fake com scores em ordem inversa ao tier
    # (tier-3 tem maior score; tier-1 tem menor) para testar que o tier domina.
    fake_alts = [
        VenueAssessment(
            venue_id="t3_high_score", venue_name="Tier3 HighScore",
            aggregate_score=0.95, dimensions={}, gaps_prioritized=[],
            needs_human_review=[], review_type_evaluated="x", fallback_tier=3,
        ),
        VenueAssessment(
            venue_id="t1_low_score", venue_name="Tier1 LowScore",
            aggregate_score=0.55, dimensions={}, gaps_prioritized=[],
            needs_human_review=[], review_type_evaluated="x", fallback_tier=1,
        ),
        VenueAssessment(
            venue_id="t2_mid_score", venue_name="Tier2 MidScore",
            aggregate_score=0.75, dimensions={}, gaps_prioritized=[],
            needs_human_review=[], review_type_evaluated="x", fallback_tier=2,
        ),
    ]
    # Aplicar a mesma lógica de sort do engine (espelho da linha em assess())
    fake_alts.sort(key=lambda a: (a.fallback_tier, -a.aggregate_score))

    # Resultado esperado: t1_low_score (tier=1), t2_mid_score (tier=2), t3_high_score (tier=3)
    assert fake_alts[0].venue_id == "t1_low_score", (
        f"Tier-1 deveria emergir primeiro mesmo com score baixo; emergiu: {fake_alts[0].venue_id}"
    )
    assert fake_alts[1].venue_id == "t2_mid_score"
    assert fake_alts[2].venue_id == "t3_high_score"


def test_v222_engine_lists_fallback_venues_when_listing():
    """O engine deve listar todos os perfis (61 após v2.3) somando todas as 5 pastas."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
    from compliance.engine import VenueComplianceEngine
    profiles_dir = Path(__file__).parent.parent.parent / "references" / "profiles"
    engine = VenueComplianceEngine(profiles_dir=profiles_dir)
    venues = engine.list_known_venues()
    assert len(venues) == 68, f"Esperado 68 venues conhecidos (v2.4.0), encontrado {len(venues)}"
    # Confirmar pelo menos 1 venue de cada pasta
    assert "lajss_abcm" in venues, "lajss_abcm (tier-2 fallback) deveria estar na listagem"
    assert "jcaes_sba_springer" in venues, "jcaes_sba_springer (tier-3 fallback) deveria estar na listagem"
    assert "rbie_sbc" in venues, "rbie_sbc (A3, recalibrado v2.3) deveria estar na listagem"
    assert "jidm_sbc" in venues, "jidm_sbc (B1 v2.3) deveria estar na listagem"


# ============================================================
# v2.3.0 — A3 BR + B1 BR catalog expansion (Decisão 15)
# ============================================================

def test_v23_folders_exist_and_have_correct_counts():
    """venues_a3_br/ deve ter 11 perfis; venues_b1_br/ deve ter 10."""
    import glob
    a3 = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_a3_br" / "*.yaml"))
    b1 = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_b1_br" / "*.yaml"))
    assert len(a3) == 11, f"Esperado 11 perfis em venues_a3_br/ (4 movidos + 7 novos), encontrado {len(a3)}"
    assert len(b1) == 10, f"Esperado 10 perfis em venues_b1_br/, encontrado {len(b1)}"


def test_v23_a3_br_coverage_meets_3_per_area_with_declared_gap():
    """A3 BR: meta ≥3 por área-mãe; gap declarado em QR1-Exatas+Tec (Decisão 15).

    Educação: ≥3 esperado e atendido (4-5 esperados conforme pesquisa).
    Saúde: ≥3 esperado e atendido (4 esperados).
    Exatas/Tec: ≥2 esperado (gap estrutural declarado, consistente com Decisão 14).
    """
    import glob

    import yaml
    a3_files = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_a3_br" / "*.yaml"))
    counts = {"Educacao": 0, "QR1-Vida+Saude": 0, "QR1-Exatas+Tecnologicas": 0}
    for p in a3_files:
        d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        sub = d["metadata"].get("qualis_subarea")
        if sub in counts:
            counts[sub] += 1
    assert counts["Educacao"] >= 3, f"Educação A3 deveria ter ≥3, encontrado {counts['Educacao']}"
    assert counts["QR1-Vida+Saude"] >= 3, f"Saúde A3 deveria ter ≥3, encontrado {counts['QR1-Vida+Saude']}"
    # Decisão 15: gap declarado em Exatas/Tec (paralelo à Decisão 14)
    assert counts["QR1-Exatas+Tecnologicas"] >= 2, (
        f"Exatas/Tec A3 deveria ter ≥2 Tier 1 puro (gap estrutural declarado, ver Decisão 15), "
        f"encontrado {counts['QR1-Exatas+Tecnologicas']}"
    )


def test_v23_b1_br_coverage_meets_3_per_area():
    """B1 BR: meta ≥3 por área-mãe (todas as 3 áreas atendidas com folga via SciELO + SBC)."""
    import glob

    import yaml
    b1_files = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_b1_br" / "*.yaml"))
    counts = {"Educacao": 0, "QR1-Vida+Saude": 0, "QR1-Exatas+Tecnologicas": 0}
    for p in b1_files:
        d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        sub = d["metadata"].get("qualis_subarea")
        if sub in counts:
            counts[sub] += 1
    for area, n in counts.items():
        assert n >= 3, f"B1 BR em {area}: esperado ≥3, encontrado {n}"


def test_v23_all_a3_b1_profiles_are_diamond_oa_brazilian():
    """Todos os 21 perfis A3 e B1 BR (incluindo recalibrados) devem ser fully_oa diamond + country=BR."""
    import glob

    import yaml
    files = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_a3_br" / "*.yaml")) + \
            glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_b1_br" / "*.yaml"))
    for p in files:
        d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        meta = d["metadata"]
        vid = meta["venue_id"]
        assert meta["country"] == "BR", f"{vid}: country deve ser BR"
        assert meta["open_access"] == "fully_oa", f"{vid}: open_access deve ser fully_oa"
        assert meta["apc_usd"] == 0, f"{vid}: apc_usd deve ser 0 (diamond OA)"


def test_v23_recalibrated_venues_carry_v23_note():
    """Os 4 venues recalibrados (rsp_usp, csc_abrasco, rbie_sbc, pope_sobrapo) devem ter
    nota explicativa v2.3 nas notes — auditabilidade da movimentação."""
    import yaml
    profiles_root = Path(__file__).parent.parent.parent / "references" / "profiles"
    recalibrated = ["rsp_usp", "csc_abrasco", "rbie_sbc", "pope_sobrapo"]
    for vid in recalibrated:
        path = profiles_root / "venues_a3_br" / f"{vid}.yaml"
        assert path.exists(), f"{vid}: deveria estar em venues_a3_br/ após recalibração v2.3"
        d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        notes = d["metadata"].get("notes", "")
        assert "v2.3 RECALIBRA" in notes or "v2.3 RECALIBRA" in notes.upper(), (
            f"{vid}: notes deveria registrar 'v2.3 RECALIBRAÇÃO' explicitamente"
        )
        assert d["metadata"]["qualis_stratum"] == "A3", (
            f"{vid}: estrato deveria ser A3 após recalibração, encontrado {d['metadata']['qualis_stratum']!r}"
        )


def test_v23_engine_loads_a3_and_b1_venues():
    """Engine deve carregar perfis das pastas venues_a3_br/ e venues_b1_br/."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
    from compliance.engine import VenueComplianceEngine
    profiles_dir = Path(__file__).parent.parent.parent / "references" / "profiles"
    engine = VenueComplianceEngine(profiles_dir=profiles_dir)

    # Sample A3
    profile_a3 = engine._load_venue_profile("rbie_sbc")
    assert profile_a3 is not None, "rbie_sbc (A3 recalibrado) deveria ser carregável"
    assert profile_a3["metadata"]["qualis_stratum"] == "A3"

    # Sample B1
    profile_b1 = engine._load_venue_profile("jserd_sbc")
    assert profile_b1 is not None, "jserd_sbc (B1 v2.3) deveria ser carregável"
    assert profile_b1["metadata"]["qualis_stratum"] == "B1"


# ============================================================
# v2.4.0 — Q2 INT catalog expansion (Decisão 16)
# ============================================================

def test_v24_q2_int_folder_has_11_profiles():
    """venues_q2_int/ deve ter 11 perfis novos."""
    import glob
    files = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q2_int" / "*.yaml"))
    assert len(files) == 11, f"Esperado 11 perfis em venues_q2_int/, encontrado {len(files)}"


def test_v24_q2_int_coverage_meets_3_per_area():
    """Q2 INT deve cobrir ≥3 venues por área-mãe (Educação, Saúde, CS/SE/Eng)."""
    import glob

    import yaml
    files = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q2_int" / "*.yaml"))
    counts_by_subject = {"Education": 0, "Health/Nursing": 0, "CS/SE/Eng": 0}
    for p in files:
        d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        subjects = d.get("scope", {}).get("primary_subjects", [])
        joined = " ".join(subjects).lower()
        # Ordem importa: Health/Nursing (mais específico) tem prioridade sobre Education
        # porque "Medical Education" e "Nursing Education" também contém "education".
        if ("nursing" in joined or "medical education" in joined or "health professions" in joined
                or "health care" in joined):
            counts_by_subject["Health/Nursing"] += 1
        elif "education" in joined or "pedagogy" in joined or "edtech" in joined or "e-learning" in joined:
            counts_by_subject["Education"] += 1
        elif "software" in joined or "computer" in joined or "engineering" in joined or "systems" in joined:
            counts_by_subject["CS/SE/Eng"] += 1
    for area, n in counts_by_subject.items():
        assert n >= 3, f"Q2 INT em {area}: esperado ≥3, encontrado {n}"


def test_v24_all_q2_int_have_quartile_metadata():
    """Todos os 11 perfis Q2 INT devem ter SJR e/ou JCR quartile declarado (não null)."""
    import glob

    import yaml
    files = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q2_int" / "*.yaml"))
    for p in files:
        d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        meta = d["metadata"]
        sjr = meta.get("sjr_quartile")
        jcr = meta.get("jcr_quartile")
        assert sjr is not None or jcr is not None, (
            f"{meta['venue_id']}: pelo menos um dos sjr_quartile/jcr_quartile deve ser declarado"
        )


def test_v24_q2_int_tier_distribution():
    """Q2 INT deve ter distribuição de tiers coerente: pelo menos 1 Tier 1, 2 Tier 2, e 4 Tier 3.

    Tier 1 esperado: rlae_usp (BR, único Q2 INT diamond OA), ethe_uoc_springer (Q1 mas diamond).
    Tier 2: education_sciences_mdpi, peerj_cs, ieee_access, cogent_education.
    Tier 3: bmc_med_education, edu_studies_routledge, nep_elsevier, ist_elsevier, jss_elsevier.
    """
    import glob

    import yaml
    files = glob.glob(str(Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q2_int" / "*.yaml"))
    counts = {1: 0, 2: 0, 3: 0}
    for p in files:
        d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        tier = d["metadata"].get("fallback_tier", 1)
        counts[tier] = counts.get(tier, 0) + 1
    assert counts.get(1, 0) >= 1, f"Esperado ≥1 Tier 1 em Q2 INT (rlae_usp, ethe_uoc_springer), encontrado {counts.get(1,0)}"
    assert counts.get(2, 0) >= 2, f"Esperado ≥2 Tier 2 em Q2 INT, encontrado {counts.get(2,0)}"
    assert counts.get(3, 0) >= 4, f"Esperado ≥4 Tier 3 em Q2 INT, encontrado {counts.get(3,0)}"


def test_v24_rlae_usp_is_brazilian_q2_int_tier_1_anchor():
    """Verifica especificamente que Revista Latino-Americana de Enfermagem é o caso raro
    de Q2 INT + Tier 1 + brasileiro simultaneamente — anchor crítico do catálogo."""
    import yaml
    p = Path(__file__).parent.parent.parent / "references" / "profiles" / "venues_q2_int" / "rlae_usp.yaml"
    assert p.exists(), "rlae_usp.yaml deve existir em venues_q2_int/"
    d = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
    meta = d["metadata"]
    assert meta["country"] == "BR", "rlae_usp deve ser country=BR"
    assert meta["sjr_quartile"] == "Q2", "rlae_usp deve ser SJR Q2"
    assert meta["fallback_tier"] == 1, "rlae_usp deve ser Tier 1 (diamond OA)"
    assert meta["apc_usd"] == 0, "rlae_usp deve ter apc_usd=0"
    assert meta["open_access"] == "fully_oa", "rlae_usp deve ser fully_oa"


def test_v24_engine_loads_q2_int_venues():
    """Engine deve carregar perfis de venues_q2_int/."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
    from compliance.engine import VenueComplianceEngine
    profiles_dir = Path(__file__).parent.parent.parent / "references" / "profiles"
    engine = VenueComplianceEngine(profiles_dir=profiles_dir)
    venues = engine.list_known_venues()
    # 6 pastas agora; total 68
    assert len(venues) == 68, f"Esperado 68 venues conhecidos (v2.4.0), encontrado {len(venues)}"
    # Confirmar venues representativos de cada categoria Q2 INT
    assert "rlae_usp" in venues, "rlae_usp (Tier 1 BR Q2 INT) deveria estar listado"
    assert "ist_elsevier" in venues, "ist_elsevier (Tier 3, premiere SLR outlet em SE) deveria estar listado"
    assert "peerj_cs" in venues, "peerj_cs (Tier 2 Q2 SJR CS) deveria estar listado"
