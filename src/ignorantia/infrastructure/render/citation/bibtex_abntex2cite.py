"""``BibTexAbntex2CiteFormatter`` — ABNT NBR 6023:2018 BibTeX entries.

Tailored for the LaTeX ``abntex2cite`` package (numeric variant —
``abntex2-num``). Differences vs the ``plain`` style:

* Author surnames are uppercased (``SILVA, J. P.``).
* ``@phdthesis`` / ``@mastersthesis`` are emitted directly (no
  generic ``@thesis``).
* ``@misc`` carries a ``howpublished`` field for legislation and
  AV resources, since NBR 6023 §8.20 requires the medium to appear
  inline.
* DOI emitted as ``doi`` (the abntex2cite package renders it in
  the canonical ABNT format with ``Disponível em:`` prefix).
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

_TYPE_OVERRIDES: dict[str, str] = {
    "thesis": "phdthesis",
    "dissertation": "mastersthesis",
    "legislation": "misc",
    "av_resource": "misc",
}


class BibTexAbntex2CiteFormatter(BibTexEntryFormatterPort):
    """ABNT NBR 6023:2018 BibTeX entries (abntex2cite numeric)."""

    @property
    def style(self) -> BibTexStyle:
        """Return :class:`BibTexStyle.ABNTEX2`."""
        return BibTexStyle.ABNTEX2

    def format_entry(self, ref: Reference, *, key: str) -> str:
        """Return the ``@<type>{<key>, …}`` entry in ABNT shape."""
        entry_type = bibtex_entry_type(ref, _TYPE_OVERRIDES)
        author_field = " and ".join(_uppercase_surname(a) for a in ref.authors)
        fields: list[str | None] = [
            render_field("author", author_field),
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
                        " and ".join(_uppercase_surname(e) for e in ref.book_editors)
                        if ref.book_editors
                        else None,
                    )
                )
        elif ref.type == "conference":
            fields.append(render_field("booktitle", ref.venue))
            fields.append(render_field("address", ref.location))
        elif ref.type in ("thesis", "dissertation"):
            fields.append(render_field("school", ref.institution))
            fields.append(render_field("address", ref.location))
        elif ref.type in ("legislation", "av_resource"):
            # NBR 6023 §8.20 — the medium / publication channel
            # is mandatory for these reference types.
            fields.append(render_field("howpublished", ref.venue or "Recurso eletrônico"))

        fields.append(render_field("pages", _abnt_pages(ref.pages)))
        fields.append(render_int_field("year", ref.year))
        fields.append(render_field("doi", ref.doi))
        fields.append(render_field("url", ref.url))
        fields.append(render_field("urldate", ref.accessed))

        body = ",\n".join(f for f in fields if f is not None)
        return f"@{entry_type}{{{key},\n{body}\n}}"


def _uppercase_surname(formatted_name: str) -> str:
    """Return ``"SILVA, J. P."`` for input ``"Silva, J. P."``.

    NBR 6023:2018 §8.1.1 requires surnames in capitals. Inputs
    lacking a comma (single-token names, institutional authors)
    are uppercased entirely.
    """
    if "," not in formatted_name:
        return formatted_name.upper()
    surname, rest = formatted_name.split(",", 1)
    return f"{surname.upper()},{rest}"


def _abnt_pages(pages: str | None) -> str | None:
    """Convert ``"100-110"`` → ``"100--110"`` for BibTeX page ranges."""
    if pages is None or "-" not in pages or "--" in pages:
        return pages
    return pages.replace("-", "--")
