"""Shared helpers for BibTeX entry formatters.

Every concrete :class:`BibTexEntryFormatterPort` implementation
needs the same building blocks: BibTeX-character escaping, mapping
from the v3 ``Reference.type`` vocabulary to BibTeX entry types,
and stable field formatting (uppercase surnames, et al. for many
authors, etc.). This module factors those out so the four
style-specific adapters carry only their style-specific decisions.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference

# BibTeX special characters that must be escaped in field values.
# Backslash must be escaped first to avoid double-escaping the
# substitutions below.
_BIBTEX_ESCAPES: tuple[tuple[str, str], ...] = (
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
)

# Reference.type → default BibTeX entry type. Style-specific
# adapters can override per-type if their style uses a different
# entry name (e.g. abntex2cite uses ``@phdthesis`` and
# ``@mastersthesis`` rather than a generic ``@thesis``).
_DEFAULT_TYPE_MAP: dict[str, str] = {
    "article": "article",
    "book": "book",
    "book_chapter": "incollection",
    "thesis": "phdthesis",
    "dissertation": "mastersthesis",
    "conference": "inproceedings",
    "electronic": "online",
    "legislation": "misc",
    "av_resource": "misc",
    "website": "online",
}


def escape_bibtex(text: str) -> str:
    """Return ``text`` with BibTeX special characters escaped.

    Idempotent in the sense that escaping an already-escaped string
    does NOT yield correct BibTeX — callers should escape exactly
    once. Used by every formatter on every field-value before
    embedding.
    """
    out = text
    for raw, replacement in _BIBTEX_ESCAPES:
        out = out.replace(raw, replacement)
    return out


def bibtex_entry_type(ref: Reference, overrides: dict[str, str] | None = None) -> str:
    """Map ``ref.type`` to its BibTeX entry name.

    Args:
        ref: The reference whose type to translate.
        overrides: Per-style overrides (e.g. abntex2 uses
            ``phdthesis`` / ``mastersthesis`` instead of a generic
            ``thesis``). Falls back to the default map.

    Returns:
        The entry-type string without the leading ``@`` (the
        formatter prepends the ``@`` when assembling the entry).
    """
    if overrides and ref.type in overrides:
        return overrides[ref.type]
    return _DEFAULT_TYPE_MAP.get(ref.type, "misc")


def format_authors_lastname_first(authors: tuple[str, ...]) -> str:
    """Return BibTeX ``author = {…}`` value with names joined by ``and``.

    Authors come in as already-formatted strings (``"Silva, J. P."``);
    BibTeX takes them verbatim joined by the literal ``and`` keyword.
    Empty author tuples return an empty string so callers can omit
    the field.
    """
    if not authors:
        return ""
    return " and ".join(escape_bibtex(a) for a in authors)


def render_field(name: str, value: str | None) -> str | None:
    r"""Return ``"<name> = {<value>}"`` or ``None`` if value is empty.

    The caller assembles the entry by joining non-``None`` values
    with ``,\\n    ``.
    """
    if value is None or value == "":
        return None
    return f"    {name} = {{{escape_bibtex(value)}}}"


def render_int_field(name: str, value: int | None) -> str | None:
    """Same as :func:`render_field` for an integer (year, volume).

    BibTeX accepts integers without braces but conventional output
    wraps them too. Returns ``None`` when ``value`` is ``None``.
    """
    if value is None:
        return None
    return f"    {name} = {{{value}}}"
