"""Testes v2.19.0 — Sprint 4: parsers reais (F15) + testes integração mock HTTP (F16)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "searches"))


# ============ F15: parser RSS LA Referencia ============

MOCK_RSS_LA_REFERENCIA = '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
  <title>LA Referencia Search Results</title>
  <item>
    <title>Letramento digital de idosos: revisao</title>
    <link>https://www.lareferencia.info/vufind/Record/123</link>
    <description>Resumo do artigo.</description>
    <dc:creator>Silva, Ana</dc:creator>
    <dc:creator>Pereira, Bruno</dc:creator>
    <dc:date>2023-05-15</dc:date>
    <dc:language>por</dc:language>
  </item>
  <item>
    <title>Alfabetizacion digital adultos</title>
    <link>https://www.lareferencia.info/vufind/Record/456</link>
    <description>Resumen breve.</description>
    <dc:creator>Gonzalez, Maria</dc:creator>
    <dc:date>2022-08-01</dc:date>
    <dc:language>spa</dc:language>
  </item>
  <item>
    <title>Article from 2018</title>
    <link>https://www.lareferencia.info/vufind/Record/789</link>
    <dc:creator>Smith, John</dc:creator>
    <dc:date>2018-03-01</dc:date>
    <dc:language>eng</dc:language>
  </item>
</channel>
</rss>'''.encode("utf-8")


def test_la_referencia_parses_rss_to_normalized_items():
    """F15: parser RSS LA Referencia retorna items normalizados."""
    import search_la_referencia as sla
    items = sla._parse_rss_xml(MOCK_RSS_LA_REFERENCIA)
    assert len(items) == 3

    # Item 1: pt, 2 authors
    assert items[0]["title"].startswith("Letramento")
    assert items[0]["language"] == "pt"  # "por" → "pt"
    assert items[0]["year"] == 2023
    assert len(items[0]["authors"]) == 2

    # Item 2: es, 1 author
    assert items[1]["language"] == "es"  # "spa" → "es"
    assert items[1]["year"] == 2022

    # Item 3: en
    assert items[2]["language"] == "en"  # "eng" → "en"
    assert items[2]["year"] == 2018


def test_la_referencia_parser_handles_malformed_xml():
    """F15: parser não falha com XML inválido — retorna lista vazia."""
    import search_la_referencia as sla
    items = sla._parse_rss_xml(b"<not><valid></xml>")
    assert items == []


def test_la_referencia_parser_skips_items_without_title():
    """F15: items sem title são descartados (defesa a feeds quebrados)."""
    import search_la_referencia as sla
    bad_rss = '''<?xml version="1.0"?>
<rss><channel>
  <item><link>http://x/1</link></item>
  <item><title>Valid item</title></item>
</channel></rss>'''.encode("utf-8")
    items = sla._parse_rss_xml(bad_rss)
    assert len(items) == 1
    assert items[0]["title"] == "Valid item"


# ============ F16: testes integração com mock HTTP ============

def test_la_referencia_real_request_uses_parser_via_mock(tmp_path):
    """F16: simula urllib.urlopen → adapter retorna items parseados, não raw_size_bytes vazio."""
    import search_la_referencia as sla

    # Mock urlopen para retornar bytes RSS válidos
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_RSS_LA_REFERENCIA
    mock_response.__enter__ = lambda self: self
    mock_response.__exit__ = lambda *args: None

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = sla._real_request(
            query="letramento digital", year_start=2020, year_end=2026,
            max_results=10, throttle=0, timeout=10,
        )

    assert result["source"] == "la_referencia"
    assert result["method"] == "LA_REFERENCIA_REAL"
    assert "results" in result
    # 2018 deve ser filtrado por janela; restam 2 items
    assert len(result["results"]) == 2
    assert result["total_results"] == 2


def test_la_referencia_real_request_handles_http_error():
    """F16: HTTPError no urllib é capturado e retorna método _ERROR."""
    import search_la_referencia as sla
    import urllib.error
    err = urllib.error.HTTPError(url="x", code=503, msg="Service Unavailable",
                                    hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err):
        result = sla._real_request("q", 2020, 2026, 10, 0, 10)
    assert result["method"] == "LA_REFERENCIA_REAL_ERROR"
    assert "error" in result


def test_la_referencia_real_no_year_filter_keeps_all():
    """F16: sem janela temporal, parser retorna todos."""
    import search_la_referencia as sla
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_RSS_LA_REFERENCIA
    mock_response.__enter__ = lambda self: self
    mock_response.__exit__ = lambda *args: None

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = sla._real_request(
            query="x", year_start=0, year_end=0,
            max_results=10, throttle=0, timeout=10,
        )

    assert len(result["results"]) == 3


def test_la_referencia_max_results_truncates():
    """F16: max_results limita output."""
    import search_la_referencia as sla
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_RSS_LA_REFERENCIA
    mock_response.__enter__ = lambda self: self
    mock_response.__exit__ = lambda *args: None

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = sla._real_request(
            query="x", year_start=2015, year_end=2026,
            max_results=2, throttle=0, timeout=10,
        )

    assert len(result["results"]) == 2  # truncado para max_results
    # total_results pode reportar 3 (todos parsed) com results truncado
    assert result["total_results"] >= 2
