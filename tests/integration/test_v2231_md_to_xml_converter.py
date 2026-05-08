"""Fix 18 / Phase 1 — MD→XML converter (RS-42 dogfood remediation).

The converter wraps Markdown reference documents in a tiny semantic XML
envelope so that subsequent phases can bundle same-stage documents into
single artifacts (cutting the production-package file count below the
220 ceiling) without losing the human-readable Markdown body. These tests
pin the converter contract:

  - The XML envelope is well-formed (parses with stdlib ``xml.etree``).
  - The Markdown body round-trips intact via the CDATA payload.
  - ``id``, ``path``, ``type``, ``lang``, ``title`` are populated correctly
    from path + content heuristics.
  - The converter neutralizes ``]]>`` sequences that would otherwise close
    the CDATA section prematurely.
  - Directory mode preserves layout when writing ``*.xml`` siblings.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))


# ── helpers ─────────────────────────────────────────────────────────────


def _parse(xml_text: str) -> ET.Element:
    return ET.fromstring(xml_text)


def _extract_markdown(xml_text: str) -> str:
    """Return the CDATA payload of the ``<markdown>`` element.

    ``xml.etree`` collapses CDATA into ordinary text on parse, which is what
    we want for the round-trip assertion (the body must equal the source MD
    semantically, even if whitespace differs at the edges).
    """
    root = _parse(xml_text)
    md_elem = root.find("markdown")
    assert md_elem is not None
    return (md_elem.text or "").strip()


# ── core contract ───────────────────────────────────────────────────────


def test_convert_file_emits_well_formed_xml(tmp_path):
    from migrate_md_to_xml import convert_file
    src = tmp_path / "abnt.md"
    src.write_text(
        "# ABNT — Norma brasileira\n\n"
        "Conjunto de normas da Associação Brasileira de Normas Técnicas.\n",
        encoding="utf-8",
    )
    xml = convert_file(src, doc_type="citation-style", lang="pt-BR", repo_root=tmp_path)
    root = _parse(xml)
    assert root.tag == "doc"
    assert root.attrib["id"] == "abnt"
    assert root.attrib["type"] == "citation-style"
    assert root.attrib["lang"] == "pt-BR"


def test_convert_file_extracts_h1_as_title(tmp_path):
    from migrate_md_to_xml import convert_file
    src = tmp_path / "apa.md"
    src.write_text("# APA — American Psychological Association\n\nBody.\n", encoding="utf-8")
    xml = convert_file(src, repo_root=tmp_path)
    root = _parse(xml)
    title = root.find("title")
    assert title is not None
    assert title.text == "APA — American Psychological Association"


def test_convert_file_falls_back_to_filename_when_no_h1(tmp_path):
    from migrate_md_to_xml import convert_file
    src = tmp_path / "ad-hoc-doc.md"
    src.write_text("Body without H1.\n", encoding="utf-8")
    xml = convert_file(src, repo_root=tmp_path)
    title = _parse(xml).find("title")
    assert title is not None
    assert title.text == "Ad Hoc Doc"


def test_convert_file_round_trips_body_via_cdata(tmp_path):
    from migrate_md_to_xml import convert_file
    body = (
        "# Title\n\n"
        "Conteúdo com **negrito**, *itálico* e `código`.\n\n"
        "- Bullet 1\n"
        "- Bullet 2\n\n"
        "| Coluna A | Coluna B |\n"
        "|---|---|\n"
        "| 1 | 2 |\n"
    )
    src = tmp_path / "doc.md"
    src.write_text(body, encoding="utf-8")
    xml = convert_file(src, repo_root=tmp_path)
    extracted = _extract_markdown(xml)
    # The CDATA round-trip must preserve every line of the body.
    for line in body.strip().splitlines():
        assert line in extracted


def test_convert_file_neutralizes_cdata_close_in_body(tmp_path):
    """A literal ``]]>`` inside the body would otherwise close the CDATA
    section. The converter must split it (``]]]]><![CDATA[>``) so the XML
    stays well-formed and a parser can reassemble the body."""
    from migrate_md_to_xml import convert_file
    src = tmp_path / "tricky.md"
    src.write_text("# Tricky\n\nLook out for ]]> in code blocks.\n", encoding="utf-8")
    xml = convert_file(src, repo_root=tmp_path)
    # Must still be well-formed.
    root = _parse(xml)
    assert root.tag == "doc"
    # And the original ``]]>`` text must have survived to the parsed output.
    md_elem = root.find("markdown")
    assert md_elem is not None
    assert "]]>" in (md_elem.text or "")


def test_convert_file_includes_portable_path_when_repo_root_supplied(tmp_path):
    from migrate_md_to_xml import convert_file
    nested = tmp_path / "references" / "citation-styles"
    nested.mkdir(parents=True)
    src = nested / "abnt.md"
    src.write_text("# ABNT\n", encoding="utf-8")
    xml = convert_file(src, doc_type="citation-style", repo_root=tmp_path)
    root = _parse(xml)
    # Path should be the repo-relative one, not absolute.
    assert root.attrib["path"] == "references/citation-styles/abnt.md"


def test_infer_type_from_directory_fragment():
    from migrate_md_to_xml import infer_type
    assert infer_type(Path("references/citation-styles/abnt.md")) == "citation-style"
    assert infer_type(Path("references/databases/portuguese.md")) == "database-catalog"
    assert infer_type(Path("references/modes/mode-01.md")) == "mode-spec"
    assert infer_type(Path("references/claude-chat-tasks/foo.md")) == "chat-task"
    # Falls back to "document" when no fragment matches.
    assert infer_type(Path("nowhere/random.md")) == "document"


def test_explicit_type_overrides_inference(tmp_path):
    from migrate_md_to_xml import convert_file
    src = tmp_path / "anything.md"
    src.write_text("# Anything\n", encoding="utf-8")
    xml = convert_file(src, doc_type="custom-type", repo_root=tmp_path)
    assert _parse(xml).attrib["type"] == "custom-type"


def test_convert_file_omits_lang_attribute_when_not_provided(tmp_path):
    from migrate_md_to_xml import convert_file
    src = tmp_path / "doc.md"
    src.write_text("# Doc\n", encoding="utf-8")
    xml = convert_file(src, repo_root=tmp_path)
    assert "lang=" not in xml.split(">\n", 1)[0]  # no lang in opening tag


# ── directory mode ──────────────────────────────────────────────────────


def test_convert_directory_writes_xml_siblings_preserving_layout(tmp_path):
    from migrate_md_to_xml import convert_directory
    src_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    (src_dir / "nested").mkdir(parents=True)
    (src_dir / "a.md").write_text("# A\n", encoding="utf-8")
    (src_dir / "nested" / "b.md").write_text("# B\n", encoding="utf-8")

    written = convert_directory(
        src_dir, out_dir, doc_type="document", lang=None, repo_root=tmp_path,
    )
    assert (out_dir / "a.xml").exists()
    assert (out_dir / "nested" / "b.xml").exists()
    assert {p.name for p in written} == {"a.xml", "b.xml"}


def test_convert_directory_dry_run_does_not_write(tmp_path, capsys):
    from migrate_md_to_xml import convert_directory
    src_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    src_dir.mkdir()
    (src_dir / "doc.md").write_text("# Doc\n", encoding="utf-8")

    convert_directory(
        src_dir, out_dir, doc_type="document", lang=None,
        repo_root=tmp_path, dry_run=True,
    )
    assert not out_dir.exists() or not list(out_dir.rglob("*.xml"))
    captured = capsys.readouterr()
    assert "dry-run" in captured.out


# ── CLI ─────────────────────────────────────────────────────────────────


def test_cli_single_file_round_trip(tmp_path):
    from migrate_md_to_xml import main
    src = tmp_path / "doc.md"
    src.write_text("# Doc\n\nBody.\n", encoding="utf-8")
    out = tmp_path / "doc.xml"
    rc = main([str(src), "--out", str(out), "--type", "test"])
    assert rc == 0
    assert out.exists()
    root = _parse(out.read_text(encoding="utf-8"))
    assert root.attrib["type"] == "test"


def test_cli_errors_when_directory_source_lacks_out_dir(tmp_path):
    from migrate_md_to_xml import main
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    rc = main([str(src_dir)])
    assert rc == 2


def test_cli_errors_when_file_source_lacks_out(tmp_path):
    from migrate_md_to_xml import main
    src = tmp_path / "doc.md"
    src.write_text("# Doc\n", encoding="utf-8")
    rc = main([str(src)])
    assert rc == 2


def test_cli_errors_when_source_does_not_exist(tmp_path):
    from migrate_md_to_xml import main
    rc = main([str(tmp_path / "nope.md")])
    assert rc != 0
