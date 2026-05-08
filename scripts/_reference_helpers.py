"""Reference-list schema helpers.

Fix 17 of the RS-42 dogfood remediation series. The dogfood transcripts
diagnosed a schema clash: ``content["references"]`` was being consumed as
``list[str]`` by ``render_latex.py`` and ``render_docx_abnt.py`` (which
passed each entry directly to ``_escape_latex`` / ``doc.add_paragraph``),
and as ``list[dict]`` by ``generate_assessment.py`` (which called
``r.get("doi")`` / ``r.get("url")``) and ``render_v2.py`` (whose function
signature declares ``list[dict]``).

Manuscripts shaped as ``list[str]`` worked in PDF/DOCX but broke
``generate_assessment.py`` with ``AttributeError``. Manuscripts shaped as
``list[dict]`` broke PDF/DOCX rendering with the dict's ``repr()`` text in
the output.

Fix 17 establishes a canonical schema and provides helpers that accept
both shapes (backward compatibility):

Canonical schema (preferred shape going forward)::

    {
        "references": [
            {
                "citation": "FERREIRA, A. ...",  # rendered ABNT/IEEE/APA string
                "doi": "10.1590/abc123",          # optional
                "url": "https://...",             # optional
                "isbn": "978-...",                # optional (books)
                "type": "article",                # optional metadata
            },
            ...
        ]
    }

Helpers in this module:

- :func:`render_reference_string` — accepts ``str`` or ``dict`` and returns
  the human-readable citation string for printing in PDF/DOCX/HTML.
- :func:`extract_doi` — accepts ``str`` or ``dict`` and returns the DOI
  (parsed from the string for legacy entries; from ``ref["doi"]`` for
  canonical entries).
- :func:`extract_url` — same as above for URLs.
- :func:`normalize_reference` — converts either shape into the canonical
  dict form.
"""

from __future__ import annotations

import re
from typing import Mapping

# Regex sourced from Crossref's documented DOI pattern.
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
_URL_RE = re.compile(r"\bhttps?://\S+\b")


def render_reference_string(ref: object) -> str:
    """Return the human-readable citation string for a reference entry.

    Accepts either:

    * ``str`` — assumed to be already-formatted (legacy ``list[str]`` schema).
      Returned unchanged.
    * ``Mapping`` (``dict``-like) with ``"citation"`` key — returned unchanged.
    * ``Mapping`` without ``"citation"`` — falls back to first non-empty value
      among ``"text"``, ``"title"``; if none, returns ``str(ref)``.

    Empty / ``None`` inputs return the empty string.
    """
    if ref is None:
        return ""
    if isinstance(ref, str):
        return ref
    if isinstance(ref, Mapping):
        for key in ("citation", "text", "title"):
            value = ref.get(key)
            if isinstance(value, str) and value.strip():
                return value
        # No usable string field — best-effort fallback.
        return str(ref)
    # Other types (int, list, etc.) — coerce to str.
    return str(ref)


def extract_doi(ref: object) -> str | None:
    """Return the DOI for a reference entry, or ``None`` if absent.

    For ``dict`` entries with a ``"doi"`` key, returns that value when truthy.
    For ``str`` entries, parses the DOI from the citation text using the
    Crossref-documented pattern. Returns ``None`` when no DOI is present.
    """
    if ref is None:
        return None
    if isinstance(ref, Mapping):
        doi = ref.get("doi")
        if isinstance(doi, str) and doi.strip():
            return doi.strip()
        # Try parsing from the citation field as fallback.
        citation = ref.get("citation")
        if isinstance(citation, str):
            match = _DOI_RE.search(citation)
            if match:
                return match.group(0)
        return None
    if isinstance(ref, str):
        match = _DOI_RE.search(ref)
        return match.group(0) if match else None
    return None


def extract_url(ref: object) -> str | None:
    """Return the URL for a reference entry, or ``None`` if absent."""
    if ref is None:
        return None
    if isinstance(ref, Mapping):
        url = ref.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
        citation = ref.get("citation")
        if isinstance(citation, str):
            match = _URL_RE.search(citation)
            if match:
                return match.group(0)
        return None
    if isinstance(ref, str):
        match = _URL_RE.search(ref)
        return match.group(0) if match else None
    return None


def normalize_reference(ref: object) -> dict:
    """Convert a reference entry into the canonical dict form.

    Strings become ``{"citation": <str>}`` with DOI/URL parsed when present.
    Dicts pass through with missing fields back-filled from the citation
    text. Other types coerce via ``str()``.
    """
    if isinstance(ref, Mapping):
        out = dict(ref)
        if "citation" not in out:
            out["citation"] = render_reference_string(ref)
        if "doi" not in out:
            doi = extract_doi(ref)
            if doi:
                out["doi"] = doi
        if "url" not in out:
            url = extract_url(ref)
            if url:
                out["url"] = url
        return out
    citation = render_reference_string(ref)
    out: dict = {"citation": citation}
    doi = extract_doi(ref)
    if doi:
        out["doi"] = doi
    url = extract_url(ref)
    if url:
        out["url"] = url
    return out


def normalize_references(refs: object) -> list[dict]:
    """Apply :func:`normalize_reference` to every entry of ``refs``.

    Accepts ``None`` (returns empty list), a single entry (wraps in list),
    or any iterable.
    """
    if refs is None:
        return []
    if isinstance(refs, (str, Mapping)):
        return [normalize_reference(refs)]
    try:
        return [normalize_reference(r) for r in refs]
    except TypeError:
        # Non-iterable — best-effort.
        return [normalize_reference(refs)]
