r"""``BibTexIEEEtranFormatter`` — entries for ``\\bibliographystyle{IEEEtran}``.

Differences vs ``plain``:

* Author names emitted in BibTeX's ``First Last`` order (no
  surname-comma-initials inversion). The IEEEtran package handles
  the rotation to inline ``J. P. Silva`` form when the bibliography
  is rendered.
* ``number`` field is dropped — IEEEtran uses ``number`` only when
  no ``volume`` is given, so we only emit it for the ``article``
  case where ``volume`` is missing (rare).
* ``booktitle`` for inproceedings includes the conference name in
  full; IEEEtran abbreviates at render-time.
"""

from __future__ import annotations

from ignorantia.domain.render.entities import Reference
from ignorantia.domain.render.ports.bibtex_entry_formatter_port import (
    BibTexEntryFormatterPort,
    BibTexStyle,
)
from ignorantia.infrastructure.render.citation._bibtex_common import (
    bibtex_entry_type,
    render_field,
    render_int_field,
)


class BibTexIEEEtranFormatter(BibTexEntryFormatterPort):
    """``IEEEtran`` style BibTeX entries."""

    @property
    def style(self) -> BibTexStyle:
        """Return :class:`BibTexStyle.IEEETRAN`."""
        return BibTexStyle.IEEETRAN

    def format_entry(self, ref: Reference, *, key: str) -> str:
        """Return the ``@<type>{<key>, …}`` entry in IEEEtran shape."""
        entry_type = bibtex_entry_type(ref)
        author_field = " and ".join(_first_last(a) for a in ref.authors)
        fields: list[str | None] = [
            render_field("author", author_field),
            render_field("title", ref.title),
        ]

        if ref.type == "article":
            fields.append(render_field("journal", ref.venue))
            fields.append(render_field("volume", ref.volume))
            # IEEEtran prefers volume; emit number only when both
            # volume is missing AND issue is present.
            if not ref.volume:
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


def _first_last(formatted_name: str) -> str:
    """Convert ``"Silva, J. P."`` → ``"J. P. Silva"`` for IEEEtran.

    Single-token names pass through unchanged. The IEEEtran package
    expects names in ``First Last`` order; it handles the visual
    inversion at render-time.
    """
    if "," not in formatted_name:
        return formatted_name
    surname, rest = formatted_name.split(",", 1)
    return f"{rest.strip()} {surname.strip()}"


def _normalise_pages(pages: str | None) -> str | None:
    if pages is None or "-" not in pages or "--" in pages:
        return pages
    return pages.replace("-", "--")
