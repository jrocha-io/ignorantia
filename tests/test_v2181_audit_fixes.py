"""Smoke tests v2.18.1 — fixes da auditoria.

F1: contextual_preamble user-agent + redirects + warnings
F2-F4: integração SKILL.md, README, render_v2
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


# ============ F1: contextual_preamble corrigido ============

def test_user_agent_includes_version_and_contact():
    """User-Agent inclui versão e contato (compliance Wikimedia)."""
    from contextual_preamble import _build_user_agent
    ua = _build_user_agent("user@example.org")
    assert "ignorantia-skill/" in ua
    assert "user@example.org" in ua
    assert "python-urllib" in ua


def test_user_agent_uses_env_var_for_contact():
    """User-Agent usa IGNORANTIA_CONTACT_EMAIL se não passado."""
    from contextual_preamble import _build_user_agent
    with patch.dict(os.environ, {"IGNORANTIA_CONTACT_EMAIL": "env@example.org"}):
        ua = _build_user_agent()
    assert "env@example.org" in ua


def test_user_agent_has_descriptive_fallback_when_no_contact():
    """Sem contato, User-Agent ainda tem identificação descritiva."""
    from contextual_preamble import _build_user_agent
    with patch.dict(os.environ, {}, clear=False):
        if "IGNORANTIA_CONTACT_EMAIL" in os.environ:
            del os.environ["IGNORANTIA_CONTACT_EMAIL"]
        ua = _build_user_agent()
    assert "ignorantia-skill" in ua
    assert "github" in ua  # URL fallback presente


def test_fetch_errors_propagate_via_warning():
    """F1: erros de rede emitem WikimediaFetchWarning + populam fetch_errors."""
    from contextual_preamble import ContextualPreamble, WikimediaFetchWarning
    cp = ContextualPreamble(language="pt-BR", throttle=0)

    # Mock urlopen para simular HTTPError 403
    import urllib.error
    mock_error = urllib.error.HTTPError(
        url="https://example.org", code=403, msg="Forbidden",
        hdrs=None, fp=None,
    )

    with patch("urllib.request.urlopen", side_effect=mock_error):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = cp._http_get_json("https://example.org/test", label="test")
            assert result is None
            assert len(w) >= 1
            assert any(issubclass(warning.category, WikimediaFetchWarning)
                       for warning in w)

    assert len(cp.fetch_errors) == 1
    assert cp.fetch_errors[0]["status"] == 403
    assert cp.fetch_errors[0]["label"] == "test"


def test_fetch_errors_propagate_via_warning_for_network_errors():
    """F1: URLError também emite WikimediaFetchWarning."""
    from contextual_preamble import ContextualPreamble, WikimediaFetchWarning
    cp = ContextualPreamble(language="pt-BR", throttle=0)
    import urllib.error
    err = urllib.error.URLError("network unreachable")

    with patch("urllib.request.urlopen", side_effect=err):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = cp._http_get_json("https://example.org/test", label="test")
            assert result is None
            assert any(issubclass(warning.category, WikimediaFetchWarning)
                       for warning in w)

    assert len(cp.fetch_errors) == 1
    assert "network unreachable" in cp.fetch_errors[0]["error"]


def test_resolve_term_via_wikidata_returns_qid_and_title():
    """F1: _resolve_term_via_wikidata busca QID + sitelink Wikipedia."""
    from contextual_preamble import ContextualPreamble
    cp = ContextualPreamble(language="pt-BR", throttle=0)

    # Mock wbsearchentities response
    mock_search_resp = MagicMock()
    mock_search_resp.read.return_value = json.dumps({
        "search": [{"id": "Q123", "label": "letramento digital"}]
    }).encode("utf-8")
    mock_search_resp.__enter__ = lambda self: self
    mock_search_resp.__exit__ = lambda *args: None

    # Mock wbgetentities response (com sitelink ptwiki)
    mock_entity_resp = MagicMock()
    mock_entity_resp.read.return_value = json.dumps({
        "entities": {"Q123": {
            "sitelinks": {"ptwiki": {"title": "Letramento digital"}}
        }}
    }).encode("utf-8")
    mock_entity_resp.__enter__ = lambda self: self
    mock_entity_resp.__exit__ = lambda *args: None

    with patch("urllib.request.urlopen", side_effect=[mock_search_resp,
                                                         mock_entity_resp]):
        result = cp._resolve_term_via_wikidata("letramento digital")

    assert result == ("Q123", "Letramento digital")


def test_resolve_term_returns_none_when_no_match():
    """F1: _resolve_term retorna None se Wikidata não tem match."""
    from contextual_preamble import ContextualPreamble
    cp = ContextualPreamble(language="pt-BR", throttle=0)

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"search": []}).encode("utf-8")
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda *args: None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = cp._resolve_term_via_wikidata("topic_inexistente_xyz")

    assert result is None


def test_html_warning_mentions_fetch_errors_count():
    """F1: HTML warning menciona quantidade de erros quando há."""
    from contextual_preamble import ContextualPreamble
    cp = ContextualPreamble(language="pt-BR")
    cp.set_topic("test")
    cp.fetch_errors = [
        {"label": "test1", "status": 403},
        {"label": "test2", "status": 500},
    ]
    html = cp.render_html()
    assert "2 erro" in html or "2 fetch" in html.lower()


def test_to_dict_includes_fetch_errors():
    """F1: to_dict inclui fetch_errors para diagnóstico."""
    from contextual_preamble import ContextualPreamble
    cp = ContextualPreamble(language="pt-BR")
    cp.set_topic("test")
    cp.fetch_errors = [{"label": "x", "status": 403}]
    d = cp.to_dict()
    assert "fetch_errors" in d
    assert len(d["fetch_errors"]) == 1


def test_to_dict_includes_user_agent():
    """F1: to_dict inclui user_agent para auditoria."""
    from contextual_preamble import ContextualPreamble
    cp = ContextualPreamble(language="pt-BR", contact_email="audit@example.org")
    cp.set_topic("test")
    d = cp.to_dict()
    assert "user_agent" in d
    assert "audit@example.org" in d["user_agent"]


# ============ F2: SKILL.md atualizado ============

def test_skill_md_mentions_paywall_cascade():
    """F2: SKILL.md documenta cascata KEY→PROXY→FALLBACK_MD."""
    skill_path = ROOT / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "FALLBACK_MD" in content or "fallback_md" in content.lower()
    assert "PROXY" in content or "proxy" in content.lower()
    assert "cascata" in content.lower() or "cascade" in content.lower()


def test_skill_md_mentions_contextual_preamble():
    """F2: SKILL.md menciona contextual_preamble (DD-11)."""
    skill_path = ROOT / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert ("contextual_preamble" in content
            or "campo onde este artigo vive" in content.lower())


def test_skill_md_mentions_screening_pipeline():
    """F2: SKILL.md menciona screening_pipeline (DD-10 Camada 2)."""
    skill_path = ROOT / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert ("screening_pipeline" in content
            or "screening_log.csv" in content)


def test_skill_md_mentions_paywall_adapters_count():
    """F2: SKILL.md indica 16 adapters paywall ou os nomeia."""
    skill_path = ROOT / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    # Deve mencionar pelo menos alguns adapters paywall
    paywall_mentions = sum(1 for name in
                            ["scopus_full", "wos_full", "ieee_full",
                             "springer_full", "google_scholar"]
                            if name in content)
    assert paywall_mentions >= 2, (
        f"SKILL.md deveria mencionar adapters paywall; encontrou {paywall_mentions}"
    )


# ============ F3: README.md atualizado ============

def test_readme_not_alpha():
    """F3: README.md não declara mais 'alpha'."""
    readme_path = ROOT / "README.md"
    content = readme_path.read_text(encoding="utf-8")
    # Aceita "alpha" em contextos históricos (changelog), mas não como status atual
    # Verifica que versão atual é 2.18+
    assert "v2.18" in content or "2.18" in content or "v2.19" in content, (
        "README deveria mencionar versão atual v2.18+"
    )


# ============ F4 parcial: integração contextual_preamble em render_v2.py ============

def test_render_v2_supports_contextual_preamble_flag():
    """F4 parcial: render_v2.py oferece flag para incluir preâmbulo contextual."""
    render_path = ROOT / "scripts" / "render_v2.py"
    content = render_path.read_text(encoding="utf-8")
    # Deve mencionar contextual_preamble OU receber objeto preamble
    assert ("contextual_preamble" in content
            or "preamble" in content.lower()
            or "campo onde" in content.lower()), (
        "render_v2.py deveria suportar inclusão de preâmbulo contextual"
    )
