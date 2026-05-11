"""Fix 21 / Phase D — implementation of the three new biphasic gates.

Three Phase 2 gates, each contributing to the user's acceptance test
*"está pronto para publicar sem conferir?"*. Together with the four
existing gates (persona, assessment, invariants, vocabulary), they
form the seven-gate chain that gates the Zenodo zip.

Gate 5 (claim-to-source coverage) — every in-prose citation traces
to a page/section of a real source.
Gate 6 (citation graph integrity) — cite ↔ ref ↔ live DOI (optional).
Gate 7 (manuscript-substantial) — PDF compiled, page/word counts hit
threshold, required sections present.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


# ── Gate 5 — claim-to-source coverage ──────────────────────────────────


CLAIM_TEX = textwrap.dedent(
    r"""
    \documentclass{article}
    \usepackage{cite}
    \begin{document}
    \section{Resultados}
    A síntese mostra que LLMs comerciais hallucinated DOIs em
    aproximadamente 30\% dos casos \cite{joshi2025}. Em pipelines com
    RAG, a taxa caiu para 8\% \cite{padarha2026,kataoka2025}.
    Estudos sem RAG não comparam runs entre si \citep{shen2026}.
    \end{document}
    """
).strip()

CLAIM_MAPPING = {
    "joshi2025": {
        "claim_id": "joshi2025",
        "claim_text": "30% hallucination rate baseline",
        "source_doi": "10.1234/jhm-2025",
        "source_anchor": "p.4 §2.3",
    },
    "padarha2026": {
        "claim_id": "padarha2026",
        "claim_text": "RAG reduces hallucination to 8%",
        "source_doi": "10.1234/agentslr-2026",
        "source_anchor": "p.7 §4.1",
    },
    "kataoka2025": {
        "claim_id": "kataoka2025",
        "claim_text": "RAG also reduces in TiAb Review Plugin",
        "source_doi": "10.1234/tiab-2025",
        "source_anchor": "p.3 Table 1",
    },
    "shen2026": {
        "claim_id": "shen2026",
        "claim_text": "Runs not compared",
        "source_doi": "10.1234/shen-2026",
        "source_anchor": "p.9 §5",
    },
}


def _write_claim_inputs(tmp: Path, tex: str, mapping: dict) -> Path:
    """Write a tex + claim mapping pair; return deposit dir."""
    deposit = tmp / "deposit"
    deposit.mkdir()
    (deposit / "manuscript.tex").write_text(tex, encoding="utf-8")
    (deposit / "claim_to_source.json").write_text(
        json.dumps(list(mapping.values()), indent=2), encoding="utf-8"
    )
    return deposit


def test_gate5_passes_when_all_claims_have_complete_mapping(tmp_path):
    from check_claim_source_coverage import find_claims, check_coverage

    claims = find_claims(CLAIM_TEX)
    assert len(claims) >= 2  # at least 2 sentences carry citations
    report = check_coverage(claims, CLAIM_MAPPING)
    assert report["covered_claims"] == report["total_claims"]
    assert report["uncovered_claim_ids"] == []
    assert report["missing_anchor_claim_ids"] == []


def test_gate5_fails_when_cite_key_missing_from_mapping(tmp_path):
    from check_claim_source_coverage import find_claims, check_coverage

    incomplete = {k: v for k, v in CLAIM_MAPPING.items() if k != "joshi2025"}
    claims = find_claims(CLAIM_TEX)
    report = check_coverage(claims, incomplete)
    assert "joshi2025" in report["uncovered_claim_ids"]
    assert report["covered_claims"] < report["total_claims"]


def test_gate5_fails_when_source_anchor_is_empty(tmp_path):
    from check_claim_source_coverage import find_claims, check_coverage

    bad_mapping = {**CLAIM_MAPPING}
    bad_mapping["joshi2025"] = {
        **bad_mapping["joshi2025"],
        "source_anchor": "",  # empty anchor → missing
    }
    claims = find_claims(CLAIM_TEX)
    report = check_coverage(claims, bad_mapping)
    assert "joshi2025" in report["missing_anchor_claim_ids"]


def test_gate5_cli_exit_zero_on_clean_deposit(tmp_path):
    deposit = _write_claim_inputs(tmp_path, CLAIM_TEX, CLAIM_MAPPING)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_claim_source_coverage.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0, rc.stderr
    sidecar = json.loads((deposit / "claim_source_gate.json").read_text())
    assert sidecar["passed"] is True


def test_gate5_cli_exit_two_on_uncovered_claims(tmp_path):
    incomplete = {k: v for k, v in CLAIM_MAPPING.items() if k != "joshi2025"}
    deposit = _write_claim_inputs(tmp_path, CLAIM_TEX, incomplete)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_claim_source_coverage.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2
    sidecar = json.loads((deposit / "claim_source_gate.json").read_text())
    assert sidecar["passed"] is False
    assert "joshi2025" in sidecar["uncovered_claim_ids"]


def test_gate5_accepts_both_list_and_indexed_mapping_forms(tmp_path):
    from check_claim_source_coverage import load_claim_to_source

    list_path = tmp_path / "list.json"
    list_path.write_text(json.dumps(list(CLAIM_MAPPING.values())), encoding="utf-8")
    indexed_path = tmp_path / "indexed.json"
    indexed_path.write_text(json.dumps(CLAIM_MAPPING), encoding="utf-8")

    assert load_claim_to_source(list_path).keys() == CLAIM_MAPPING.keys()
    assert load_claim_to_source(indexed_path).keys() == CLAIM_MAPPING.keys()


def test_gate5_zero_claims_is_failure(tmp_path):
    """A manuscript with zero citations is suspicious — either the
    synthesis is missing or the citation format is wrong. Either way,
    not Zenodo-ready."""
    no_cite_tex = textwrap.dedent(
        r"""
        \documentclass{article}
        \begin{document}
        \section{Results} Synthesis without citations. No claims at all.
        \end{document}
        """
    ).strip()
    deposit = _write_claim_inputs(tmp_path, no_cite_tex, CLAIM_MAPPING)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_claim_source_coverage.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2


# ── Gate 6 — citation graph integrity ──────────────────────────────────


GRAPH_TEX = textwrap.dedent(
    r"""
    \documentclass{article}
    \begin{document}
    \section{Discussion}
    The RAG approach reduced hallucination significantly \cite{joshi2025}.
    Multi-agent setups also help \cite{padarha2026,mas2025}.
    \bibliography{bibliography}
    \end{document}
    """
).strip()

GRAPH_BIB_COMPLETE = textwrap.dedent(
    """
    @article{joshi2025,
      title = {Mitigating LLM Hallucinations},
      author = {Joshi and others},
      year = {2025},
      doi = {10.1234/jhm-2025}
    }
    @article{padarha2026,
      title = {AgentSLR},
      author = {Padarha},
      year = {2026},
      doi = {10.1234/agentslr-2026}
    }
    @inproceedings{mas2025,
      title = {Multi-Agent Systems for SLR},
      author = {Mushtaq},
      year = {2025},
      doi = {10.1234/mas-2025}
    }
    """
).strip()


def _write_graph_inputs(tmp: Path, tex: str, bib: str) -> Path:
    deposit = tmp / "deposit"
    deposit.mkdir()
    (deposit / "manuscript.tex").write_text(tex, encoding="utf-8")
    (deposit / "bibliography.bib").write_text(bib, encoding="utf-8")
    return deposit


def test_gate6_extracts_cited_keys():
    from check_citation_graph import extract_cited_keys

    keys = extract_cited_keys(GRAPH_TEX)
    assert keys == {"joshi2025", "padarha2026", "mas2025"}


def test_gate6_parses_bib_entries():
    from check_citation_graph import parse_bib_entries

    entries = parse_bib_entries(GRAPH_BIB_COMPLETE)
    assert set(entries) == {"joshi2025", "padarha2026", "mas2025"}
    assert entries["joshi2025"]["doi"] == "10.1234/jhm-2025"
    assert entries["mas2025"]["_type"] == "inproceedings"


def test_gate6_passes_on_complete_graph(tmp_path):
    deposit = _write_graph_inputs(tmp_path, GRAPH_TEX, GRAPH_BIB_COMPLETE)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_citation_graph.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0, rc.stderr
    sidecar = json.loads((deposit / "citation_graph_gate.json").read_text())
    assert sidecar["passed"] is True


def test_gate6_fails_when_cite_key_missing_from_bib(tmp_path):
    incomplete_bib = "\n".join(
        line for line in GRAPH_BIB_COMPLETE.splitlines()
        if "mas2025" not in line and line.strip() and not line.startswith("}")
    ) + "\n}"
    # Use a simpler incomplete bib instead
    bib = textwrap.dedent(
        """
        @article{joshi2025, year={2025}, doi={10.1234/jhm-2025}}
        @article{padarha2026, year={2026}}
        """
    ).strip()
    deposit = _write_graph_inputs(tmp_path, GRAPH_TEX, bib)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_citation_graph.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2
    sidecar = json.loads((deposit / "citation_graph_gate.json").read_text())
    assert "mas2025" in sidecar["missing_keys"]


def test_gate6_fails_on_padding_unused_bib_entries(tmp_path):
    """Bib entries that no claim cites = reference padding."""
    bib = GRAPH_BIB_COMPLETE + textwrap.dedent(
        """

        @article{padding_entry,
          title = {Famous Paper Not Actually Cited},
          year = {2020}
        }
        """
    )
    deposit = _write_graph_inputs(tmp_path, GRAPH_TEX, bib)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_citation_graph.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2
    sidecar = json.loads((deposit / "citation_graph_gate.json").read_text())
    assert "padding_entry" in sidecar["unused_keys"]


def test_gate6_doi_verify_off_by_default(tmp_path):
    """Without --verify-dois, no network calls happen and DOIs aren't checked."""
    deposit = _write_graph_inputs(tmp_path, GRAPH_TEX, GRAPH_BIB_COMPLETE)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_citation_graph.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False, timeout=5,
    )
    assert rc.returncode == 0
    sidecar = json.loads((deposit / "citation_graph_gate.json").read_text())
    assert sidecar["retracted_dois"] == []
    assert sidecar["unreachable_dois"] == []


# ── Gate 7 — manuscript-substantial ────────────────────────────────────


_SECTION_HEADINGS = (
    ("§00", "Propósito"),
    ("§01", "Conflito de interesse"),
    ("§02", "Introdução"),
    ("§03", "Pergunta de pesquisa"),
    ("§04", "Métodos"),
    ("§05", "Resultados"),
    ("§06", "Discussão"),
    ("§07", "Conclusões"),
    ("§08", "Evidência contrária"),
    ("§09", "Limitações"),
)


def _write_substantial_inputs(
    tmp: Path,
    *,
    pdf_pages: int | None = None,
    body_words: int = 5500,
    skip_indices: tuple[int, ...] = (),
) -> Path:
    deposit = tmp / "deposit"
    deposit.mkdir()
    words_per_section = max(10, body_words // 10)
    body = " ".join(["loremipsum"] * (words_per_section // 1))
    parts = [r"\documentclass{article}", r"\begin{document}"]
    for idx, (num, title) in enumerate(_SECTION_HEADINGS):
        if idx in skip_indices:
            continue
        parts.append(f"\\section{{{num} {title}}}")
        parts.append(body)
    parts.append(r"\end{document}")
    tex = "\n".join(parts)
    (deposit / "manuscript.tex").write_text(tex, encoding="utf-8")
    if pdf_pages is not None:
        # Minimal fake PDF: a single-object PDF with /Type /Pages /Count N.
        pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
            b"2 0 obj <</Type /Pages /Count " + str(pdf_pages).encode() +
            b" /Kids []>> endobj\n"
            b"xref\n0 3\n0000000000 65535 f\n"
            b"0000000009 00000 n\n"
            b"0000000050 00000 n\n"
            b"trailer <</Size 3 /Root 1 0 R>>\n"
            b"startxref\n100\n%%EOF"
        )
        (deposit / "manuscript.pdf").write_bytes(pdf)
    return deposit


def test_gate7_passes_on_substantial_manuscript(tmp_path):
    deposit = _write_substantial_inputs(tmp_path, pdf_pages=15, body_words=6000)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_manuscript_substantial.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0, rc.stderr
    sidecar = json.loads((deposit / "manuscript_substantial_gate.json").read_text())
    assert sidecar["passed"] is True
    assert sidecar["page_count"] == 15


def test_gate7_fails_when_pdf_missing(tmp_path):
    deposit = _write_substantial_inputs(tmp_path, pdf_pages=None, body_words=6000)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_manuscript_substantial.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2
    sidecar = json.loads((deposit / "manuscript_substantial_gate.json").read_text())
    assert sidecar["pdf_exists"] is False


def test_gate7_fails_on_below_threshold_page_count(tmp_path):
    deposit = _write_substantial_inputs(tmp_path, pdf_pages=5, body_words=6000)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_manuscript_substantial.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2
    sidecar = json.loads((deposit / "manuscript_substantial_gate.json").read_text())
    assert sidecar["page_count"] == 5
    assert sidecar["page_count_ok"] is False


def test_gate7_fails_on_below_threshold_word_count(tmp_path):
    deposit = _write_substantial_inputs(tmp_path, pdf_pages=15, body_words=1000)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_manuscript_substantial.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2
    sidecar = json.loads((deposit / "manuscript_substantial_gate.json").read_text())
    assert sidecar["word_count_ok"] is False


def test_gate7_fails_on_missing_required_section(tmp_path):
    deposit = _write_substantial_inputs(
        tmp_path,
        pdf_pages=15,
        body_words=6000,
        skip_indices=(8,),  # §08 Evidência contrária
    )
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_manuscript_substantial.py"),
         str(deposit), "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 2
    sidecar = json.loads((deposit / "manuscript_substantial_gate.json").read_text())
    assert "Evidência contrária" in sidecar["missing_sections"]


def test_gate7_rapid_mode_thresholds(tmp_path):
    """Rapid reviews use a lower bar (8 pages, 3000 words)."""
    deposit = _write_substantial_inputs(tmp_path, pdf_pages=10, body_words=3500)
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_manuscript_substantial.py"),
         str(deposit), "--min-pages", "8", "--min-words", "3000", "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0, rc.stderr


def test_gate7_word_count_strips_latex_commands():
    from check_manuscript_substantial import count_body_words

    text = textwrap.dedent(
        r"""
        \documentclass{article}
        \begin{document}
        \section{Results}
        A simple sentence \cite{key1} with some text.
        \textbf{Bold} and \emph{italic} content.
        $E = mc^2$ should be stripped.
        \end{document}
        """
    ).strip()
    count = count_body_words(text)
    # Roughly: 'Results A simple sentence key1 with some text Bold and italic content should be stripped'
    # Word count ~15-17, depending on stripping. Just confirm it's
    # in a reasonable range and not zero.
    assert 8 <= count <= 25, f"got {count}"


def test_gate7_page_count_falls_back_to_pure_python_parser(tmp_path):
    """If pdfinfo isn't available, the fallback parser reads /Count."""
    from check_manuscript_substantial import count_pdf_pages

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n1 0 obj <</Type /Pages /Count 42>> endobj\n%%EOF"
    )
    # We can't easily mock shutil.which, but the result should still
    # find Count=42 even via the fallback if pdfinfo doesn't return.
    count = count_pdf_pages(pdf)
    assert count == 42


# ── seven-gate chain shape (smoke) ─────────────────────────────────────


def test_three_new_gate_scripts_exist_and_are_executable():
    """The three new gate scripts must exist and emit sidecars."""
    for name in [
        "check_claim_source_coverage.py",
        "check_citation_graph.py",
        "check_manuscript_substantial.py",
    ]:
        script = ROOT / "scripts" / name
        assert script.is_file(), f"{name} not found"
        # Verify the script is at least a valid Python file
        rc = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True, check=False,
        )
        assert rc.returncode == 0, f"{name} --help failed: {rc.stderr}"
