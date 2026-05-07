"""``ApaCitationFormatter`` — APA Publication Manual, 7th edition.

Concrete :class:`CitationFormatterPort` for APA 7th. Author surnames
appear in mixed case (``Silva, J. P.``), inline citations use the
``(Surname, year)`` author-date form with ``&`` between two authors,
and 3+ authors collapse to ``Surname et al.``.

Italics are emitted as Markdown ``*...*`` so each renderer can map
them to the appropriate emphasis tag (HTML ``<em>``, LaTeX ``emph``)
without leaking format-specific markup into the citation Strategy.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.citation_formatter_port import CitationFormatterPort
from ignorantia.domain.render.value_objects import CitationStyle


class ApaCitationFormatter(CitationFormatterPort):
    """APA 7th edition citation Strategy."""

    @property
    def style(self) -> CitationStyle:
        """Return :class:`CitationStyle.APA`."""
        return CitationStyle.APA

    def format_reference(self, ref: Reference) -> str:
        """Return the APA 7th reference-list entry for ``ref``."""
        authors = _format_authors(ref.authors)
        year = f"({ref.year})" if ref.year else "(n.d.)"

        if ref.type == "article":
            return _format_article(ref, authors, year)
        if ref.type == "book":
            return _format_book(ref, authors, year)
        if ref.type == "book_chapter":
            return _format_book_chapter(ref, authors, year)
        if ref.type in ("thesis", "dissertation"):
            return _format_thesis_or_dissertation(ref, authors, year)
        if ref.type == "conference":
            return _format_conference(ref, authors, year)
        if ref.type in ("electronic", "website"):
            return _format_electronic(ref, authors, year)
        if ref.type == "legislation":
            return _format_legislation(ref, year)
        if ref.type == "av_resource":
            return _format_av_resource(ref, authors, year)
        raise RuntimeError(f"unhandled reference type: {ref.type!r}")

    def format_inline_citation(
        self,
        ref: Reference,
        *,
        page: str | None = None,
        index: int | None = None,
    ) -> str:
        """Return the APA 7th author-date inline citation for ``ref``."""
        del index
        sn = _inline_authors(ref.authors)
        year = str(ref.year) if ref.year else "n.d."
        if page:
            return f"({sn}, {year}, p. {page})"
        return f"({sn}, {year})"


def _format_authors(authors: tuple[str, ...]) -> str:
    if not authors:
        return ""
    formatted = [_apa_author(a) for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    if len(formatted) <= 20:
        return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"
    head = ", ".join(formatted[:19])
    return f"{head}, ... {formatted[-1]}"


def _apa_author(name: str) -> str:
    raw = name.strip()
    if "," in raw:
        last, given = raw.split(",", 1)
        return f"{_titlecase(last.strip())}, {_initials(given.strip())}"
    if " " in raw:
        given, last = raw.rsplit(" ", 1)
        return f"{_titlecase(last.strip())}, {_initials(given.strip())}"
    return _titlecase(raw)


def _titlecase(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name


def _initials(given: str) -> str:
    parts = [p for p in given.replace(".", "").split() if p]
    if not parts:
        return ""
    return ". ".join(p[0].upper() for p in parts) + "."


def _inline_authors(authors: tuple[str, ...]) -> str:
    if not authors:
        return "Anonymous"
    if len(authors) == 1:
        return _last_name(authors[0])
    if len(authors) == 2:
        return f"{_last_name(authors[0])} & {_last_name(authors[1])}"
    return f"{_last_name(authors[0])} et al."


def _last_name(name: str) -> str:
    raw = name.strip()
    if "," in raw:
        return _titlecase(raw.split(",", 1)[0].strip())
    if " " in raw:
        return _titlecase(raw.rsplit(" ", 1)[1].strip())
    return _titlecase(raw)


def _format_doi_or_url(ref: Reference) -> str:
    if ref.doi:
        return f"https://doi.org/{ref.doi}"
    if ref.url:
        return ref.url
    return ""


def _format_article(ref: Reference, authors: str, year: str) -> str:
    bits = [f"{authors} {year}.", f"{ref.title}.", f"*{ref.venue}*"]
    issue_part = ""
    if ref.volume:
        issue_part = ref.volume
        if ref.issue:
            issue_part += f"({ref.issue})"
    locator = ""
    if issue_part and ref.pages:
        locator = f", {issue_part}, {ref.pages}."
    elif issue_part:
        locator = f", {issue_part}."
    elif ref.pages:
        locator = f", {ref.pages}."
    else:
        locator = "."
    bits[-1] = bits[-1] + locator
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_book(ref: Reference, authors: str, year: str) -> str:
    bits = [f"{authors} {year}.", f"*{ref.title}*."]
    if ref.publisher:
        bits.append(f"{ref.publisher}.")
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_book_chapter(ref: Reference, authors: str, year: str) -> str:
    bits = [
        f"{authors} {year}.",
        f"{ref.chapter_title or ref.title}.",
        "In",
    ]
    if ref.book_editors:
        editors = ", ".join(_apa_author(e) for e in ref.book_editors)
        bits.append(f"{editors} (Ed.),")
    bits.append(f"*{ref.title}*")
    if ref.pages:
        bits.append(f"(pp. {ref.pages}).")
    else:
        bits[-1] = bits[-1] + "."
    if ref.publisher:
        bits.append(f"{ref.publisher}.")
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_thesis_or_dissertation(ref: Reference, authors: str, year: str) -> str:
    label = "Doctoral dissertation" if ref.type == "thesis" else "Master's thesis"
    bits = [f"{authors} {year}.", f"*{ref.title}*"]
    if ref.institution:
        bits.append(f"[{label}, {ref.institution}].")
    else:
        bits.append(f"[{label}].")
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_conference(ref: Reference, authors: str, year: str) -> str:
    bits = [f"{authors} {year}.", f"{ref.title}."]
    if ref.venue:
        bits.append(f"*{ref.venue}*")
    if ref.location:
        bits[-1] = bits[-1] + f", {ref.location}."
    elif ref.venue:
        bits[-1] = bits[-1] + "."
    if ref.publisher:
        bits.append(f"{ref.publisher}.")
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_electronic(ref: Reference, authors: str, year: str) -> str:
    head = authors or "Anonymous"
    bits = [f"{head} {year}.", f"*{ref.title}*."]
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_legislation(ref: Reference, year: str) -> str:
    bits = [f"{ref.title}, {year}."]
    if ref.venue:
        bits.append(f"{ref.venue}.")
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)


def _format_av_resource(ref: Reference, authors: str, year: str) -> str:
    head = authors or "Anonymous"
    bits = [f"{head} {year}.", f"*{ref.title}* [Audiovisual]."]
    if ref.publisher:
        bits.append(f"{ref.publisher}.")
    end = _format_doi_or_url(ref)
    if end:
        bits.append(end)
    return " ".join(bits)
