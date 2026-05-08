"""``BibTexPlainFormatter`` — default ``plain`` BibTeX style entries."""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
    BibTexEntryFormatterPort,
    BibTexStyle,
)
from ignorantia.infrastructure.render.citation._bibtex_common import (
    bibtex_entry_type,
    format_authors_lastname_first,
    render_field,
    render_int_field,
)


class BibTexPlainFormatter(BibTexEntryFormatterPort):
    r"""Default ``plain`` style — alphabetical entries, numeric labels.

    The ``plain`` style is the lowest-common-denominator BibTeX
    output: works with any ``\\bibliographystyle{plain}`` LaTeX
    document, no extra packages required.
    """

    @property
    def style(self) -> BibTexStyle:
        """Return :class:`BibTexStyle.PLAIN`."""
        return BibTexStyle.PLAIN

    def format_entry(self, ref: Reference, *, key: str) -> str:
        """Return the ``@<type>{<key>, …}`` entry for ``ref``."""
        entry_type = bibtex_entry_type(ref)
        fields: list[str | None] = [
            render_field("author", format_authors_lastname_first(ref.authors)),
            render_field("title", ref.title),
        ]

        if ref.type == "article":
            fields.append(render_field("journal", ref.venue))
            fields.append(render_field("volume", ref.volume))
            fields.append(render_field("number", ref.issue))
        elif ref.type in ("book", "book_chapter"):
            fields.append(render_field("publisher", ref.publisher))
            fields.append(render_field("address", ref.location))
            if ref.type == "book_chapter":
                fields.append(render_field("booktitle", ref.title))
                fields.append(
                    render_field(
                        "editor",
                        " and ".join(ref.book_editors) if ref.book_editors else None,
                    )
                )
        elif ref.type == "conference":
            fields.append(render_field("booktitle", ref.venue))
            fields.append(render_field("address", ref.location))
        elif ref.type in ("thesis", "dissertation"):
            fields.append(render_field("school", ref.institution))
            fields.append(render_field("address", ref.location))

        fields.append(render_field("pages", _normalise_pages(ref.pages)))
        fields.append(render_int_field("year", ref.year))
        fields.append(render_field("doi", ref.doi))
        fields.append(render_field("url", ref.url))

        body = ",\n".join(f for f in fields if f is not None)
        return f"@{entry_type}{{{key},\n{body}\n}}"


def _normalise_pages(pages: str | None) -> str | None:
    """Convert ``"100-110"`` → ``"100--110"`` (BibTeX page range)."""
    if pages is None or "-" not in pages:
        return pages
    # Replace single hyphen with the LaTeX en-dash convention used
    # in BibTeX entries; double-hyphen → triple is wrong and rare,
    # so guard against it.
    if "--" in pages:
        return pages
    return pages.replace("-", "--")
