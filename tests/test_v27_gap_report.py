"""Smoke tests do access_gap_report (v2.7.0)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


def test_gap_report_collects_only_non_oa_items():
    import access_gap_report
    payload = {
        "records": [
            {"doi": "10.1/oa", "has_legitimate_oa": True, "title": "OA artigo",
             "best_url": "https://example.org/oa"},
            {"doi": "10.2/closed", "has_legitimate_oa": False, "oa_status": "closed",
             "title": "Closed artigo", "journal_name": "Closed Journal", "year": 2024,
             "request_url_for_author": "https://oa.works/request/10.2/closed",
             "sources_tried": ["unpaywall", "oa_button"]},
            {"doi": "10.3/error", "has_legitimate_oa": False, "error": "404 not found",
             "title": "Erro artigo", "sources_tried": ["unpaywall"]},
        ]
    }
    items = access_gap_report.collect_gap_from_tier0(payload)
    # Apenas os 2 sem OA devem aparecer
    assert len(items) == 2
    dois = {i.identifier for i in items}
    assert dois == {"10.2/closed", "10.3/error"}


def test_gap_report_md_is_neutral():
    """Linguagem do relatório deve ser neutra — nem recomendar nem proibir plataformas."""
    import access_gap_report
    payload = {
        "records": [
            {"doi": "10.2/closed", "has_legitimate_oa": False, "oa_status": "closed",
             "title": "Closed artigo", "journal_name": "X", "year": 2024,
             "request_url_for_author": "https://oa.works/request/10.2/closed",
             "sources_tried": ["unpaywall", "oa_button"]},
        ]
    }
    items = access_gap_report.collect_gap_from_tier0(payload)
    md = access_gap_report.render_md(items, project_id="teste")

    # NÃO deve mencionar plataformas específicas (favorável ou desfavorável) nem juízos legais.
    text_lower = md.lower()
    excluded_terms = ["sci-hub", "scihub", "libgen", "z-library", "anna's archive",
                      "ilegal", "ilícit", "pirat"]
    for term in excluded_terms:
        assert term not in text_lower, (
            f"VIOLAÇÃO posição neutra: termo encontrado no gap report. "
            f"O relatório deve declarar o gap sem tomar posição sobre plataformas."
        )

    # DEVE mencionar que decisão é do usuário
    assert "decisão do usuário" in md or "decisão é do usuário" in md, \
        "Relatório deve declarar soberania do usuário sobre como obter os itens."


def test_gap_report_writes_md_file(tmp_path):
    import access_gap_report
    payload = {
        "records": [
            {"doi": "10.2/closed", "has_legitimate_oa": False, "oa_status": "closed",
             "title": "Test", "year": 2024, "sources_tried": ["unpaywall"]},
        ]
    }
    out = tmp_path / "gap_report.md"
    report = access_gap_report.generate_gap_report(
        payload, output_path=out, project_id="smoke_test",
        input_dir=str(tmp_path / "user_provided"),
    )
    assert out.exists()
    assert report.n_items == 1
    assert report.n_articles == 1
    content = out.read_text(encoding="utf-8")
    assert "smoke_test" in content
    assert "user_provided" in content


def test_gap_report_handles_books():
    import access_gap_report
    payload = {"records": []}
    book = access_gap_report.GapItem(
        identifier="978-0-13-468599-1",
        item_type="book",
        title="Software Engineering, 10th ed.",
        journal_or_publisher="Pearson",
        year=2015,
        status_note="paywall — comprar ou empréstimo bibliotecário",
    )
    report = access_gap_report.generate_gap_report(payload, books=[book])
    assert report.n_books == 1
    assert "978-0-13-468599-1" in report.md_text
    assert "Software Engineering" in report.md_text


def test_gap_report_no_items_renders_empty():
    """Quando todos os DOIs têm OA, relatório vazio mas válido."""
    import access_gap_report
    payload = {
        "records": [
            {"doi": "10.1/oa", "has_legitimate_oa": True, "best_url": "https://x"},
            {"doi": "10.2/oa", "has_legitimate_oa": True, "best_url": "https://y"},
        ]
    }
    report = access_gap_report.generate_gap_report(payload)
    assert report.n_items == 0
    assert "0 itens" in report.md_text
