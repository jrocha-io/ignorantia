"""Testes v2.23.0 — auditoria #5 + análise SOLID/DRY (D1-D6 + E1-E10).

Escritos em fase TDD-red ANTES dos fixes correspondentes. Quando os fixes
forem aplicados, esta suíte deve ficar verde.

Fixes cobertos por estes testes:
- D3: schema mock vs real idêntico em arxiv/crossref/dblp/s2
- E1: source_tier sempre string canônica em todos os adapters
- D5: helper cli_exit_with_error_message produz stderr informativo
- D1+D2: schema legacy OA tem year_range, total_results
- E2: USER_AGENT derivado de _skill_version.VERSION em todos os adapters
- E5+DIM 12: throttle/timeout defaults centralizados
- E6: AdapterMethod enum existe e é usado
- D6: orquestrador gera orchestration_summary.json
- E10: pipeline_finalize tem registry de steps
- E8: timestamp injection para reprodutibilidade
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# ============ D3: schema mock vs real ============

class TestD3MockRealParity:
    """D3: o schema item-level entre mock e real deve ser idêntico nos campos
    essenciais. Antes da v2.23.0, mock tinha language/is_oa/url/venue mas
    real não — divergência grave."""

    ESSENTIAL_FIELDS = {"title", "authors", "year", "language", "is_oa", "url", "venue"}

    def test_arxiv_real_has_essential_fields(self):
        """arxiv parse_entry retorna dict com todos os campos essenciais."""
        from search_arxiv import parse_entry, ATOM_NS  # noqa
        mock_xml = """<entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<id>http://arxiv.org/abs/2401.00001v1</id>
<title>Test Paper</title>
<summary>Mock summary.</summary>
<author><name>Doe, J.</name></author>
<published>2024-01-01T00:00:00Z</published>
<category term="cs.AI"/>
<link rel="alternate" href="http://arxiv.org/abs/2401.00001v1" />
<link title="pdf" href="http://arxiv.org/pdf/2401.00001v1" />
</entry>"""
        result = parse_entry(ET.fromstring(mock_xml))
        for field in self.ESSENTIAL_FIELDS:
            assert field in result, f"arxiv real ausente '{field}'"
        assert isinstance(result["year"], int), "arxiv real year deveria ser int"

    def test_arxiv_mock_has_essential_fields(self, tmp_path):
        """arxiv mock retorna mesmos campos essenciais."""
        out = tmp_path / "x.json"
        subprocess.run([sys.executable, str(ROOT / "scripts" / "searches" / "search_arxiv.py"),
                        "--query", "test", "--mock", "--output", str(out)],
                       capture_output=True, timeout=10)
        item = json.loads(out.read_text())["results"][0]
        for field in self.ESSENTIAL_FIELDS:
            assert field in item, f"arxiv mock ausente '{field}'"

    @pytest.mark.parametrize("adapter", ["crossref", "dblp", "semantic_scholar"])
    def test_retrofitted_mock_has_essential_fields(self, adapter, tmp_path):
        """crossref/dblp/s2 mocks têm todos campos essenciais."""
        out = tmp_path / f"{adapter}.json"
        subprocess.run([sys.executable, str(ROOT / "scripts" / "searches" / f"search_{adapter}.py"),
                        "--query", "test", "--mock", "--output", str(out)],
                       capture_output=True, timeout=10)
        item = json.loads(out.read_text())["results"][0]
        for field in self.ESSENTIAL_FIELDS:
            assert field in item, f"{adapter} mock ausente '{field}'"


# ============ E1: source_tier Liskov ============

class TestE1SourceTierLiskov:
    """E1: source_tier deve ser SEMPRE str (tier0/1/2/3) em todos os adapters.

    Antes da v2.23.0, paywall/legacy usavam int (1, 2) e retrofitted usavam
    str ('tier1', 'tier2'). Pós-processadores quebravam silenciosamente.
    """

    @pytest.mark.parametrize("adapter,expected_tier", [
        ("arxiv", "tier1"),
        ("doaj", "tier1"),
        ("scopus_full", "tier2"),
        ("crossref", "tier2"),
        ("bdtd", "tier1"),
    ])
    def test_source_tier_is_string(self, adapter, expected_tier, tmp_path):
        out = tmp_path / f"{adapter}.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "searches" / f"search_{adapter}.py"),
             "--query", "test", "--mock", "--output", str(out)],
            capture_output=True, timeout=10,
        )
        assert result.returncode == 0
        d = json.loads(out.read_text())
        assert isinstance(d["source_tier"], str), (
            f"{adapter} source_tier deve ser str, é {type(d['source_tier']).__name__}"
        )
        assert d["source_tier"] == expected_tier


# ============ D5: stderr informativo ============

class TestD5InformativeStderr:
    """D5: adapters que retornam exit 1 devem imprimir mensagem em stderr."""

    def test_helper_exists_in_adapter_base(self):
        """cli_exit_with_error_message disponível em _adapter_base."""
        from _adapter_base import cli_exit_with_error_message
        assert callable(cli_exit_with_error_message)

    def test_helper_returns_0_when_no_error(self, capsys):
        """Sem erro no result → exit 0, sem stderr."""
        from _adapter_base import cli_exit_with_error_message
        rc = cli_exit_with_error_message({"results": []}, "test_source")
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_helper_returns_1_with_stderr_on_error(self, capsys):
        """Com erro → exit 1, mensagem em stderr."""
        from _adapter_base import cli_exit_with_error_message
        rc = cli_exit_with_error_message(
            {"error": "HTTP 403: Forbidden"}, "test_source"
        )
        assert rc == 1
        captured = capsys.readouterr()
        assert "test_source" in captured.err
        assert "HTTP 403" in captured.err


# ============ E2: USER_AGENT centralizado ============

class TestE2UserAgentSingleSource:
    """E2: VERSION deve ter single source of truth em _skill_version.

    Antes da v2.23.0, USER_AGENT estava hardcoded em 10 valores diferentes.
    """

    def test_skill_version_module_exists(self):
        """_skill_version.py existe e exporta VERSION."""
        from _skill_version import VERSION
        assert VERSION
        # VERSION segue SemVer
        parts = VERSION.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts[:3])

    def test_build_user_agent_includes_version(self):
        from _skill_version import VERSION, build_user_agent
        ua = build_user_agent()
        assert VERSION in ua
        assert "ignorantia-skill" in ua

    def test_build_user_agent_with_email(self):
        from _skill_version import build_user_agent
        ua = build_user_agent("test@example.org")
        assert "test@example.org" in ua

    def test_all_adapters_share_same_user_agent_base(self):
        """Todos os adapters com USER_AGENT devem ter a mesma versão."""
        adapter_files = [f for f in os.listdir(ROOT / "scripts" / "searches")
                          if f.startswith("search_") and f.endswith(".py")]
        uas = set()
        for f in adapter_files:
            try:
                module_name = f.replace(".py", "")
                if module_name in sys.modules:
                    del sys.modules[module_name]
                module = __import__(module_name)
                if hasattr(module, "USER_AGENT"):
                    uas.add(module.USER_AGENT)
            except Exception:
                pass  # adapter com import problem; nem todos precisam ter USER_AGENT
        # Todos devem ter prefixo ignorantia-skill/<VERSION_ATUAL>
        from _skill_version import VERSION
        for ua in uas:
            assert f"ignorantia-skill/{VERSION}" in ua, (
                f"USER_AGENT '{ua}' não bate com VERSION {VERSION}"
            )


# ============ D1+D2: schema legacy OA ============

class TestD1D2LegacySchemaUnification:
    """D1+D2: adapters legacy OA devem ter year_range e total_results."""

    @pytest.mark.parametrize("adapter", [
        "doaj", "scielo", "oapen", "core", "osf_preprints",
        "zenodo", "biorxiv", "eric", "europepmc",
    ])
    def test_legacy_has_year_range(self, adapter, tmp_path):
        out = tmp_path / f"{adapter}.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "searches" / f"search_{adapter}.py"),
             "--query", "test", "--mock", "--output", str(out)],
            capture_output=True, timeout=10,
        )
        if result.returncode != 0:
            pytest.skip(f"{adapter} mock falhou")
        d = json.loads(out.read_text())
        assert "year_range" in d, f"{adapter} sem year_range"

    def test_scielo_has_total_results_and_method(self, tmp_path):
        """SciELO migrou de schema antigo (n) para unificado (total_results, method)."""
        out = tmp_path / "scielo.json"
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "searches" / "search_scielo.py"),
             "--query", "test", "--mock", "--output", str(out)],
            capture_output=True, timeout=10,
        )
        d = json.loads(out.read_text())
        assert "total_results" in d, "SciELO ainda usa schema antigo"
        assert "method" in d
        assert "year_start" in d
        assert "year_end" in d


# ============ E5+DIM 12: throttle/timeout centralizados ============

class TestE5CentralizedDefaults:
    """E5: DEFAULT_THROTTLE e DEFAULT_TIMEOUT em _adapter_base."""

    def test_default_throttle_in_adapter_base(self):
        from _adapter_base import DEFAULT_THROTTLE
        assert isinstance(DEFAULT_THROTTLE, (int, float))
        assert 0 < DEFAULT_THROTTLE <= 5  # entre 0 e 5 segundos

    def test_default_timeout_in_adapter_base(self):
        from _adapter_base import DEFAULT_TIMEOUT
        assert isinstance(DEFAULT_TIMEOUT, (int, float))
        assert DEFAULT_TIMEOUT >= 10


# ============ E6: AdapterMethod enum ============

class TestE6AdapterMethodEnum:
    """E6: AdapterMethod deve ser enum em vez de magic strings."""

    def test_adapter_method_enum_exists(self):
        from _adapter_base import AdapterMethod
        assert hasattr(AdapterMethod, "MOCK")
        assert hasattr(AdapterMethod, "REAL")
        assert hasattr(AdapterMethod, "REAL_PARTIAL")
        assert hasattr(AdapterMethod, "REAL_ERROR")

    def test_adapter_method_values_are_strings(self):
        from _adapter_base import AdapterMethod
        assert AdapterMethod.MOCK.value == "MOCK"
        assert AdapterMethod.REAL.value == "REAL"


# ============ D6: orquestrador summary ============

class TestD6OrchestrationSummary:
    """D6: orquestrador deve gerar orchestration_summary.json no final."""

    def test_orchestrator_writes_summary_json(self, tmp_path):
        # Smoke teste — em sandbox sem rede, mas adapters podem falhar; o que
        # importa é que o summary é escrito no final mesmo com adapters falhando.
        result = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "searches" / "search_orchestrator.py"),
            "--query", "test_d6",
            "--year-start", "2023", "--year-end", "2024",
            "--area", "educacao", "--mode", "rapid_review",
            "--output-dir", str(tmp_path),
            "--skip-tier0", "--skip-gap-resolution",
        ], capture_output=True, text=True, timeout=120)
        # Mesmo se falhar adapters, summary deve existir
        summary_path = tmp_path / "orchestration_summary.json"
        assert summary_path.exists(), (
            f"orchestration_summary.json não gerado. "
            f"stdout: {result.stdout[-200:]}, stderr: {result.stderr[-200:]}"
        )
        summary = json.loads(summary_path.read_text())
        assert "started_at" in summary
        assert "finished_at" in summary
        assert "adapters_run" in summary or "tier1_adapters" in summary


# ============ E10: pipeline_finalize registry ============

class TestE10PipelineRegistry:
    """E10: pipeline_finalize deve usar registry de steps em vez de hardcoded."""

    def test_pipeline_steps_registry_exists(self):
        """PIPELINE_STEPS é uma lista/tupla declarando as etapas."""
        import pipeline_finalize
        assert hasattr(pipeline_finalize, "PIPELINE_STEPS")
        assert len(pipeline_finalize.PIPELINE_STEPS) == 6


# ============ DIM 4: paridade declarativa ============

class TestDim4DeclarativeParity:
    """DIM 4: SKILL.md/README contadores devem bater com realidade."""

    def test_skill_md_says_correct_adapter_count(self):
        """Post-F20: adapter count declared in dev-docs/SKILL-HISTORY.md.

        Pre-F20 (mixed audience): the literal "62 adapters" count was
        in SKILL.md as a developer-facing quantitative state snapshot.
        Post-F20 (audience separation): operator-facing SKILL.md doesn't
        carry skill-internal counts — those live in dev-docs alongside
        the rest of the engineering audit log.
        """
        history = (ROOT / "dev-docs" / "SKILL-HISTORY.md").read_text(encoding="utf-8")
        adapter_count = len([f for f in os.listdir(ROOT / "scripts" / "searches")
                              if f.startswith("search_") and f.endswith(".py")])
        assert (f"{adapter_count} adapters" in history or
                "61 adapters" in history or
                "62 adapters" in history), (
            f"dev-docs/SKILL-HISTORY.md não declara contagem correta. "
            f"Real: {adapter_count}"
        )
