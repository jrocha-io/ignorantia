r"""Markdown subset → LaTeX converter.

Handles the small Markdown vocabulary used by ignorantia manuscripts:
paragraphs (blank-line separated), ``**bold**`` → ``\textbf{...}``,
``*italic*`` → ``\textit{...}``. Every other character that has a
special meaning in LaTeX (``%``, ``$``, ``&``, ``#``, ``_``, ``{``,
``}``, ``~``, ``^``, backslash) is escaped before emphasis tokens
are substituted in.
"""

from __future__ import annotations

import re

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")

_LATEX_ESCAPES: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
}


def latex_escape(text: str) -> str:
    """Escape every LaTeX special character in ``text``."""
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in text)


def markdown_to_latex(text: str) -> str:
    """Convert a Markdown subset to LaTeX source."""
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n\n".join(_paragraph(p) for p in paragraphs)


def _paragraph(p: str) -> str:
    escaped = latex_escape(p)
    escaped = _BOLD_RE.sub(r"\\textbf{\1}", escaped)
    escaped = _ITALIC_RE.sub(r"\\textit{\1}", escaped)
    return escaped
