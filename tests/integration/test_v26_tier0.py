"""Smoke tests do Tier 0 OA locator (v2.6.0)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # /home/claude/ignorantia_v2
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


def test_unpaywall_mock_known_doi_returns_oa():
    import search_unpaywall
    rec = search_unpaywall.resolve_doi("10.1186/s13643-016-0384-4",
                                        email="mock@example.org", mock=True)
    assert rec.error is None or "fixture" in (rec.error or "")
    assert rec.is_oa is True
    assert rec.best_oa_url is not None
    assert rec.oa_status == "gold"
    assert rec.best_oa_license == "cc-by"


def test_unpaywall_mock_closed_doi_returns_no_oa():
    import search_unpaywall
    rec = search_unpaywall.resolve_doi("10.0000/closed-fixture",
                                        email="mock@example.org", mock=True)
    assert rec.is_oa is False
    assert rec.oa_status == "closed"
    assert rec.best_oa_url is None


def test_unpaywall_real_without_email_fails_gracefully():
    import search_unpaywall
    rec = search_unpaywall.resolve_doi("10.1186/s13643-016-0384-4", email="", mock=False)
    assert rec.is_oa is False
    assert rec.error is not None
    assert "email" in rec.error.lower()


def test_oa_button_mock_known_doi_returns_oa():
    import search_oa_button
    rec = search_oa_button.resolve_doi("10.1186/s13643-016-0384-4", mock=True)
    assert rec.is_oa is True
    assert rec.oa_url is not None


def test_oa_button_mock_unknown_doi_returns_request_url():
    import search_oa_button
    rec = search_oa_button.resolve_doi("10.9999/unknown-fixture", mock=True)
    assert rec.is_oa is False
    assert rec.request_url is not None
    assert "oa.works/request" in rec.request_url


def test_tier0_resolver_priority_order():
    """Tier 0 unificado: Unpaywall primeiro; OAB só se Unpaywall não acha."""
    import tier0_resolver
    # DOI em ambas as fixtures — Unpaywall deve responder primeiro
    rec = tier0_resolver.resolve_doi_with_tier0(
        "10.1186/s13643-016-0384-4", email="mock@example.org", mock=True)
    assert rec.has_legitimate_oa is True
    assert rec.best_source == "unpaywall"
    assert "unpaywall" in rec.sources_tried
    assert rec.oa_status == "gold"
    # Fechado em Unpaywall, default em OAB
    rec2 = tier0_resolver.resolve_doi_with_tier0(
        "10.0000/closed-fixture", email="mock@example.org", mock=True)
    # Fixture OAB para closed-fixture devolve request_url, não is_oa
    assert rec2.has_legitimate_oa is False
    assert rec2.request_url_for_author is not None
    assert "unpaywall" in rec2.sources_tried
    assert "oa_button" in rec2.sources_tried


def test_tier0_resolver_records_metadata_even_when_no_oa():
    """Quando Unpaywall conhece o DOI mas não há OA, metadados devem ser preservados."""
    import tier0_resolver
    rec = tier0_resolver.resolve_doi_with_tier0(
        "10.0000/closed-fixture", email="mock@example.org", mock=True)
    # closed-fixture do mock Unpaywall tem oa_status='closed'
    assert rec.oa_status == "closed"


def test_decision_17_excluded_platforms():
    """Verifica que nenhuma URL de plataformas em disputa judicial aparece no código.

    A lista abaixo contém termos literais que NÃO devem ocorrer em strings/URLs no código
    automatizado do Tier 0. A presença desses tokens é o que o teste valida — eles ficam aqui
    como variável local (não exportada) com nome neutro.
    """
    import tier0_resolver
    src_files = [
        Path(tier0_resolver.__file__),
        Path(tier0_resolver.search_unpaywall.__file__),
        Path(tier0_resolver.search_oa_button.__file__),
    ]
    excluded_platform_url_tokens = [
        "sci-hub.se", "sci-hub.st", "sci-hub.ru",
        "libgen.is", "libgen.rs", "libgen.li",
    ]
    for f in src_files:
        text = f.read_text(encoding="utf-8").lower()
        for forbidden_url in excluded_platform_url_tokens:
            assert forbidden_url not in text, (
                f"VIOLAÇÃO Decisão 17: URL de plataforma excluída encontrada em {f.name}"
            )
