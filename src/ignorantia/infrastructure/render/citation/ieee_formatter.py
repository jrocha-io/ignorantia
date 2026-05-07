"""``IeeeCitationFormatter`` — IEEE numeric style.

Concrete :class:`CitationFormatterPort` for IEEE editorial style. The
inline form is a bracketed number tied to the manuscript reference
list order, so callers must pass ``index=`` to
:meth:`format_inline_citation`. When the renderer cannot supply a
position (e.g. while the reference list is still being built), the
formatter emits ``[?]`` so the caller can spot missing entries.

Author blocks render as ``J. P. Silva`` (initials before surname).
Up to six authors are listed; seven or more collapse to the first
author followed by ``et al.`` per IEEE Editorial Style §III-A.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.value_objects import CitationStyle


class IeeeCitationFormatter(CitationFormatterPort):
    """IEEE numeric citation Strategy."""

    @property
    def style(self) -> CitationStyle:
        """Return :class:`CitationStyle.IEEE`."""
        return CitationStyle.IEEE

    def format_reference(self, ref: Reference) -> str:
        """Return the IEEE reference-list entry for ``ref``."""
        authors = _format_authors(ref.authors)

        if ref.type == "article":
            return _format_article(ref, authors)
        if ref.type == "book":
            return _format_book(ref, authors)
        if ref.type == "book_chapter":
            return _format_book_chapter(ref, authors)
        if ref.type in ("thesis", "dissertation"):
            return _format_thesis_or_dissertation(ref, authors)
        if ref.type == "conference":
            return _format_conference(ref, authors)
        if ref.type in ("electronic", "website"):
            return _format_electronic(ref, authors)
        if ref.type == "legislation":
            return _format_legislation(ref)
        if ref.type == "av_resource":
            return _format_av_resource(ref, authors)
        raise RuntimeError(f"unhandled reference type: {ref.type!r}")

    def format_inline_citation(
        self,
        ref: Reference,
        *,
        page: str | None = None,
        index: int | None = None,
    ) -> str:
        """Return the IEEE bracketed-number inline citation for ``ref``."""
        del ref
        if index is None:
            return "[?]"
        if index <= 0:
            raise ValueError(f"index must be a positive integer, got {index}")
        if page:
            return f"[{index}, p. {page}]"
        return f"[{index}]"


def _format_authors(authors: tuple[str, ...]) -> str:
    if not authors:
        return ""
    formatted = [_ieee_author(a) for a in authors[:6]]
    if len(authors) > 6:
        return f"{formatted[0]} et al."
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"


def _ieee_author(name: str) -> str:
    raw = name.strip()
    if "," in raw:
        last, given = raw.split(",", 1)
        return f"{_initials(given.strip())} {_titlecase(last.strip())}"
    if " " in raw:
        given, last = raw.rsplit(" ", 1)
        return f"{_initials(given.strip())} {_titlecase(last.strip())}"
    return _titlecase(raw)


def _initials(given: str) -> str:
    parts = [p for p in given.replace(".", "").split() if p]
    if not parts:
        return ""
    return ". ".join(p[0].upper() for p in parts) + "."


def _titlecase(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name


def _format_article(ref: Reference, authors: str) -> str:
    bits = [f"{authors},", f'"{ref.title},"', f"*{ref.venue}*,"]
    locator: list[str] = []
    if ref.volume:
        locator.append(f"vol. {ref.volume}")
    if ref.issue:
        locator.append(f"no. {ref.issue}")
    if ref.pages:
        locator.append(f"pp. {ref.pages}")
    if locator:
        bits.append(", ".join(locator) + ",")
    if ref.year:
        bits.append(f"{ref.year}")
    if ref.doi:
        bits.append(f", doi: {ref.doi}.")
    else:
        bits[-1] = bits[-1] + "."
    return " ".join(bits)


def _format_book(ref: Reference, authors: str) -> str:
    bits = [f"{authors},", f"*{ref.title}*."]
    if ref.location:
        bits.append(f"{ref.location}:")
    if ref.publisher:
        sep = "," if ref.location else ""
        bits.append(f"{ref.publisher}{sep}")
    if ref.year:
        bits.append(f"{ref.year}.")
    return " ".join(bits)


def _format_book_chapter(ref: Reference, authors: str) -> str:
    bits = [f"{authors},", f'"{ref.chapter_title or ref.title},"', f"in *{ref.title}*"]
    if ref.book_editors:
        editors = ", ".join(_ieee_author(e) for e in ref.book_editors)
        bits.append(f", {editors}, Ed.")
    if ref.location:
        bits.append(f"{ref.location}:")
    if ref.publisher:
        sep = "," if ref.location else ""
        bits.append(f"{ref.publisher}{sep}")
    if ref.year:
        bits.append(f"{ref.year},")
    if ref.pages:
        bits.append(f"pp. {ref.pages}.")
    elif ref.year:
        bits[-1] = bits[-1].rstrip(",") + "."
    return " ".join(bits)


def _format_thesis_or_dissertation(ref: Reference, authors: str) -> str:
    label = "Ph.D. dissertation" if ref.type == "thesis" else "M.S. thesis"
    bits = [f"{authors},", f'"{ref.title},"', f"{label},"]
    if ref.institution:
        bits.append(f"{ref.institution},")
    if ref.location:
        bits.append(f"{ref.location},")
    if ref.year:
        bits.append(f"{ref.year}.")
    return " ".join(bits)


def _format_conference(ref: Reference, authors: str) -> str:
    bits = [f"{authors},", f'"{ref.title},"', f"in *{ref.venue}*,"]
    if ref.location:
        bits.append(f"{ref.location},")
    if ref.year:
        bits.append(f"{ref.year},")
    if ref.pages:
        bits.append(f"pp. {ref.pages}.")
    elif bits[-1].endswith(","):
        bits[-1] = bits[-1][:-1] + "."
    return " ".join(bits)


def _format_electronic(ref: Reference, authors: str) -> str:
    head = authors or "Anon."
    bits = [f"{head},", f"*{ref.title}*."]
    if ref.year:
        bits.append(f"({ref.year}).")
    if ref.url:
        bits.append(f"[Online]. Available: {ref.url}")
    if ref.accessed:
        bits.append(f". Accessed: {ref.accessed}.")
    return " ".join(bits)


def _format_legislation(ref: Reference) -> str:
    bits = [f"{ref.title}."]
    if ref.venue:
        bits.append(f"{ref.venue},")
    if ref.year:
        bits.append(f"{ref.year}.")
    return " ".join(bits)


def _format_av_resource(ref: Reference, authors: str) -> str:
    head = authors or "Anon."
    bits = [f"{head},", f"*{ref.title}* (Audiovisual)."]
    if ref.location:
        bits.append(f"{ref.location}:")
    if ref.publisher:
        sep = "," if ref.location else ""
        bits.append(f"{ref.publisher}{sep}")
    if ref.year:
        bits.append(f"{ref.year}.")
    return " ".join(bits)
