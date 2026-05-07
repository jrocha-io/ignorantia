"""``AbntCitationFormatter`` — ABNT NBR 6023:2018 + NBR 10520:2023.

Concrete :class:`CitationFormatterPort` implementing the ABNT
references and inline-citation rules. Following DD-12 (v2.9.0), ABNT
formatting is mandatory whenever the manuscript language is ``pt-BR``.

Title and venue strings are emitted with Markdown ``**...**`` markers
so renderers translate them to italics in their target format. The
formatter never injects format-specific tags (``<em>``, LaTeX ``emph``).

Authoring rules covered:

* References — article, book, book_chapter, thesis, dissertation,
  conference, electronic, website, legislation, av_resource.
* Author block — ``SOBRENOME, Iniciais.`` joined by ``;``; 4+ authors
  collapse to ``SOBRENOME et al.``; missing authors render as ``[s.a.]``.
* Final segment — ``DOI: ...`` when known, otherwise
  ``Disponível em: <URL>. Acesso em: <date>.``.
* Inline citation — author-data form ``(SILVA, 2024)`` /
  ``(SILVA; PEREIRA, 2024)`` / ``(SILVA et al., 2024)`` with
  ``, p. <page>`` suffix for direct quotations.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.value_objects import CitationStyle


class AbntCitationFormatter(CitationFormatterPort):
    """ABNT (NBR 6023:2018 + NBR 10520:2023) citation Strategy."""

    @property
    def style(self) -> CitationStyle:
        """Return :class:`CitationStyle.ABNT`."""
        return CitationStyle.ABNT

    def format_reference(self, ref: Reference) -> str:
        """Return the NBR 6023:2018 reference-list entry for ``ref``."""
        authors = _format_authors(ref.authors)
        end = _format_doi_or_url(ref)

        if ref.type == "article":
            return _format_article(ref, authors, end)
        if ref.type == "book":
            return _format_book(ref, authors, end)
        if ref.type == "book_chapter":
            return _format_book_chapter(ref, authors, end)
        if ref.type in ("thesis", "dissertation"):
            return _format_thesis_or_dissertation(ref, authors)
        if ref.type == "conference":
            return _format_conference(ref, authors, end)
        if ref.type in ("electronic", "website"):
            return _format_electronic(ref, authors, end)
        if ref.type == "legislation":
            return _format_legislation(ref, end)
        if ref.type == "av_resource":
            return _format_av_resource(ref, authors, end)
        # Reference.__post_init__ guarantees ref.type is canonical, so
        # any unhandled branch is a programming error in this module.
        raise RuntimeError(f"unhandled reference type: {ref.type!r}")

    def format_inline_citation(self, ref: Reference, *, page: str | None = None) -> str:
        """Return the NBR 10520:2023 inline (author-data) citation for ``ref``."""
        sn = _inline_authors(ref.authors)
        year = str(ref.year) if ref.year else "[s.d.]"
        if page:
            return f"({sn}, {year}, p. {page})"
        return f"({sn}, {year})"


def _format_authors(authors: tuple[str, ...]) -> str:
    if not authors:
        return "[s.a.]"
    formatted = [_author_lastname_first(a) for a in authors[:3]]
    out = "; ".join(formatted)
    if len(authors) > 3:
        out += " et al."
    return out


def _author_lastname_first(name: str) -> str:
    raw = name.strip()
    if "," in raw:
        last, given = raw.split(",", 1)
        return f"{last.strip().upper()}, {_initials(given.strip())}"
    if " " in raw:
        given, last = raw.rsplit(" ", 1)
        return f"{last.strip().upper()}, {_initials(given.strip())}"
    return raw.upper()


def _initials(given: str) -> str:
    parts = [p for p in given.replace(".", "").split() if p]
    if not parts:
        return ""
    return ". ".join(p[0].upper() for p in parts) + "."


def _inline_authors(authors: tuple[str, ...]) -> str:
    if not authors:
        return "[s.a.]"
    if len(authors) == 1:
        return _last_name_uppercase(authors[0])
    if len(authors) <= 3:
        return "; ".join(_last_name_uppercase(a) for a in authors)
    return f"{_last_name_uppercase(authors[0])} et al."


def _last_name_uppercase(name: str) -> str:
    raw = name.strip()
    if "," in raw:
        return raw.split(",", 1)[0].strip().upper()
    if " " in raw:
        return raw.rsplit(" ", 1)[1].strip().upper()
    return raw.upper()


def _format_doi_or_url(ref: Reference) -> str:
    if ref.doi:
        return f"DOI: {ref.doi}."
    if ref.url:
        if ref.accessed:
            return f"Disponível em: {ref.url}. Acesso em: {ref.accessed}."
        return f"Disponível em: {ref.url}."
    return ""


def _format_article(ref: Reference, authors: str, end: str) -> str:
    parts = [f"{authors}.", f"{ref.title}.", f"**{ref.venue}**,"]
    loc_bits: list[str] = []
    if ref.volume:
        loc_bits.append(f"v. {ref.volume}")
    if ref.issue:
        loc_bits.append(f"n. {ref.issue}")
    if ref.pages:
        loc_bits.append(f"p. {ref.pages}")
    if loc_bits:
        parts.append(", ".join(loc_bits) + ",")
    if ref.year:
        parts.append(f"{ref.year}.")
    if end:
        parts.append(end)
    return " ".join(parts)


def _format_book(ref: Reference, authors: str, end: str) -> str:
    parts = [f"{authors}.", f"**{ref.title}**."]
    if ref.location:
        parts.append(f"{ref.location}:")
    if ref.publisher:
        sep = "," if ref.location else ""
        parts.append(f"{ref.publisher}{sep}")
    if ref.year:
        parts.append(f"{ref.year}.")
    if end:
        parts.append(end)
    return " ".join(parts)


def _format_book_chapter(ref: Reference, authors: str, end: str) -> str:
    parts: list[str] = [
        f"{authors}.",
        f"{ref.chapter_title or ref.title}.",
        "In:",
    ]
    if ref.book_editors:
        parts.append(f"{_format_authors(ref.book_editors)} (org.).")
    parts.append(f"**{ref.title}**.")
    if ref.location:
        parts.append(f"{ref.location}:")
    if ref.publisher:
        sep = "," if ref.location else ""
        parts.append(f"{ref.publisher}{sep}")
    if ref.year:
        parts.append(f"{ref.year}.")
    if ref.pages:
        parts.append(f"p. {ref.pages}.")
    if end:
        parts.append(end)
    return " ".join(parts)


def _format_thesis_or_dissertation(ref: Reference, authors: str) -> str:
    label = "Tese (Doutorado em" if ref.type == "thesis" else "Dissertação (Mestrado em"
    program = f" {ref.program})" if ref.program else ")"
    bits: list[str] = [f"{authors}.", f"**{ref.title}**."]
    if ref.year:
        bits.append(f"{ref.year}.")
    bits.append(f"{label}{program}")
    bits.append("—")
    if ref.institution:
        bits.append(f"{ref.institution},")
    if ref.location:
        bits.append(f"{ref.location},")
    if ref.year:
        bits.append(f"{ref.year}.")
    return " ".join(bits)


def _format_conference(ref: Reference, authors: str, end: str) -> str:
    bits: list[str] = [f"{authors}.", f"{ref.title}.", "In:", f"**{ref.venue}**,"]
    if ref.year:
        bits.append(f"{ref.year},")
    if ref.location:
        bits.append(f"{ref.location}.")
    bits.append("**Anais** [...].")
    if ref.publisher:
        bits.append(f"{ref.publisher},")
    if ref.year:
        bits.append(f"{ref.year}.")
    if ref.pages:
        bits.append(f"p. {ref.pages}.")
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_electronic(ref: Reference, authors: str, end: str) -> str:
    bits = [f"{authors}.", f"**{ref.title}**."]
    if ref.location:
        bits.append(f"{ref.location},")
    if ref.year:
        bits.append(f"{ref.year}.")
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_legislation(ref: Reference, end: str) -> str:
    bits = [f"{ref.title}."]
    if ref.venue:
        bits.append(f"{ref.venue},")
    if ref.year:
        bits.append(f"{ref.year}.")
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_av_resource(ref: Reference, authors: str, end: str) -> str:
    bits = [f"**{ref.title}**.", f"{authors}."]
    if ref.location:
        bits.append(f"{ref.location}:")
    if ref.publisher:
        sep = "," if ref.location else ""
        bits.append(f"{ref.publisher}{sep}")
    if ref.year:
        bits.append(f"{ref.year}.")
    if end:
        bits.append(end)
    return " ".join(bits)
