"""Unit tests for the Markdown-to-LaTeX converter.

The converter handles only the subset of Markdown ignorantia
manuscripts use: paragraphs, ``**bold**``, ``*italic*``, and proper
escaping of LaTeX special characters (``%``, ``$``, ``&``, ``#``,
``_``, ``{``, ``}``, ``~``, ``^``, ``\\``).
"""

from __future__ import annotations

import pytest

from ignorantia.infrastructure.render.markdown_to_latex import markdown_to_latex


class TestParagraphSplitting:
    def test_single_paragraph(self) -> None:
        assert markdown_to_latex("Hello.") == "Hello."

    def test_two_paragraphs_joined_with_blank_line(self) -> None:
        assert markdown_to_latex("Para 1.\n\nPara 2.") == "Para 1.\n\nPara 2."

    def test_collapses_extra_blank_lines(self) -> None:
        assert markdown_to_latex("A.\n\n\n\nB.") == "A.\n\nB."


class TestEmphasis:
    def test_bold(self) -> None:
        assert markdown_to_latex("A **bold** word.") == r"A \textbf{bold} word."

    def test_italic(self) -> None:
        assert markdown_to_latex("A *italic* word.") == r"A \textit{italic} word."

    def test_bold_and_italic_in_same_paragraph(self) -> None:
        out = markdown_to_latex("**Bold** and *italic*.")
        assert r"\textbf{Bold}" in out
        assert r"\textit{italic}" in out


class TestEscaping:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("100% sure", r"100\% sure"),
            ("$5 cost", r"\$5 cost"),
            ("A & B", r"A \& B"),
            ("hash # tag", r"hash \# tag"),
            ("under_score", r"under\_score"),
            ("braces {x}", r"braces \{x\}"),
            ("tilde ~", r"tilde \textasciitilde{}"),
            ("caret ^", r"caret \textasciicircum{}"),
        ],
    )
    def test_special_char(self, raw: str, expected: str) -> None:
        assert markdown_to_latex(raw) == expected

    def test_backslash(self) -> None:
        assert markdown_to_latex("a \\ b") == r"a \textbackslash{} b"

    def test_emphasis_markers_not_escaped_inside_emphasis(self) -> None:
        # The output of bold/italic uses real LaTeX backslashes; those
        # must not get re-escaped to \textbackslash{}.
        out = markdown_to_latex("**bold**")
        assert out == r"\textbf{bold}"
