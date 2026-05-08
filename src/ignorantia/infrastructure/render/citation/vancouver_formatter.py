"""``VancouverCitationFormatter`` — ICMJE / NLM Vancouver style.

Concrete :class:`CitationFormatterPort` for the Vancouver style used
by ICMJE-aligned biomedical journals. Authors render as
``SurnameInitials`` (e.g. ``Silva JP``) with no comma or period;
titles, journal names and book titles carry no emphasis. Inline
citations are bracketed numbers driven by the same ``index=`` kwarg
the IEEE formatter uses, but rendered with parentheses ``(N)`` per
the NLM Citing Medicine convention.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.value_objects import CitationStyle


class VancouverCitationFormatter(CitationFormatterPort):
    """Vancouver/ICMJE numeric citation Strategy."""

    @property
    def style(self) -> CitationStyle:
        """Return :class:`CitationStyle.VANCOUVER`."""
        return CitationStyle.VANCOUVER

    def format_reference(self, ref: Reference) -> str:
        """Return the Vancouver/ICMJE reference-list entry for ``ref``."""
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
        """Return the Vancouver bracketed-number inline citation for ``ref``."""
        del ref
        if index is None:
            return "(?)"
        if index <= 0:
            raise ValueError(f"index must be a positive integer, got {index}")
        if page:
            return f"({index}, p. {page})"
        return f"({index})"


def _format_authors(authors: tuple[str, ...]) -> str:
    if not authors:
        return "[Anonymous]"
    formatted = [_vancouver_author(a) for a in authors[:6]]
    out = ", ".join(formatted)
    if len(authors) > 6:
        out += ", et al."
    return out


def _vancouver_author(name: str) -> str:
    raw = name.strip()
    if "," in raw:
        last, given = raw.split(",", 1)
        return f"{_titlecase(last.strip())} {_initials(given.strip())}"
    if " " in raw:
        given, last = raw.rsplit(" ", 1)
        return f"{_titlecase(last.strip())} {_initials(given.strip())}"
    return _titlecase(raw)


def _initials(given: str) -> str:
    parts = [p for p in given.replace(".", "").split() if p]
    return "".join(p[0].upper() for p in parts)


def _titlecase(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name


def _format_article(ref: Reference, authors: str) -> str:
    locator = ""
    if ref.volume:
        locator = ref.volume
        if ref.issue:
            locator += f"({ref.issue})"
        if ref.pages:
            locator += f":{ref.pages}"
    elif ref.pages:
        locator = ref.pages

    head = f"{authors}. {ref.title}. {ref.venue}."
    if ref.year:
        if locator:
            head += f" {ref.year};{locator}."
        else:
            head += f" {ref.year}."
    if ref.doi:
        head += f" doi: {ref.doi}."
    return head


def _format_book(ref: Reference, authors: str) -> str:
    head = f"{authors}. {ref.title}."
    place_pub = []
    if ref.location:
        place_pub.append(ref.location)
    if ref.publisher:
        if place_pub:
            place_pub[0] = f"{place_pub[0]}: {ref.publisher}"
        else:
            place_pub.append(ref.publisher)
    if place_pub and ref.year:
        head += f" {place_pub[0]}; {ref.year}."
    elif place_pub:
        head += f" {place_pub[0]}."
    elif ref.year:
        head += f" {ref.year}."
    return head


def _format_book_chapter(ref: Reference, authors: str) -> str:
    head = f"{authors}. {ref.chapter_title or ref.title}."
    if ref.book_editors:
        editors = ", ".join(_vancouver_author(e) for e in ref.book_editors)
        head += f" In: {editors}, editor. {ref.title}."
    else:
        head += f" In: {ref.title}."
    if ref.location:
        head += f" {ref.location}:"
        if ref.publisher:
            head += f" {ref.publisher};"
        if ref.year:
            head += f" {ref.year}."
    elif ref.publisher and ref.year:
        head += f" {ref.publisher}; {ref.year}."
    elif ref.year:
        head += f" {ref.year}."
    if ref.pages:
        head += f" p. {ref.pages}."
    return head


def _format_thesis_or_dissertation(ref: Reference, authors: str) -> str:
    label = "dissertation" if ref.type == "thesis" else "master's thesis"
    head = f"{authors}. {ref.title} [{label}]."
    if ref.location:
        head += f" {ref.location}:"
        if ref.institution:
            head += f" {ref.institution};"
        if ref.year:
            head += f" {ref.year}."
    elif ref.institution and ref.year:
        head += f" {ref.institution}; {ref.year}."
    elif ref.year:
        head += f" {ref.year}."
    return head


def _format_conference(ref: Reference, authors: str) -> str:
    head = f"{authors}. {ref.title}."
    if ref.venue:
        head += f" In: {ref.venue};"
        if ref.year:
            head += f" {ref.year};"
        if ref.location:
            head += f" {ref.location}."
    if ref.pages:
        head += f" p. {ref.pages}."
    return head


def _format_electronic(ref: Reference, authors: str) -> str:
    head = f"{authors}. {ref.title} [Internet]."
    if ref.year:
        head += f" {ref.year}"
    if ref.accessed:
        head += f" [cited {ref.accessed}]"
    head += "."
    if ref.url:
        head += f" Available from: {ref.url}"
    return head


def _format_legislation(ref: Reference) -> str:
    bits = [f"{ref.title}."]
    if ref.venue:
        bits.append(f"{ref.venue},")
    if ref.year:
        bits.append(f"{ref.year}.")
    return " ".join(bits)


def _format_av_resource(ref: Reference, authors: str) -> str:
    head = f"{authors}. {ref.title} [audiovisual]."
    if ref.location:
        head += f" {ref.location}:"
        if ref.publisher:
            head += f" {ref.publisher};"
        if ref.year:
            head += f" {ref.year}."
    elif ref.year:
        head += f" {ref.year}."
    return head
