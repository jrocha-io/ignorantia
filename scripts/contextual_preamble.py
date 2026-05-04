#!/usr/bin/env python3
"""
contextual_preamble.py — Gerador de preâmbulo contextual via Wikipedia + Wikidata
(Decisão DD-11). v2.18.1: bugs F1 corrigidos.

**NÃO é adapter de busca.** É módulo de render que gera seção intitulada
**"O campo onde este artigo vive"** distinta da Introdução.

### v2.18.1 — Correções F1 (auditoria)

1. **User-Agent compliant Wikimedia**: User-Agent agora segue a User-Agent
   policy. Aceita override via `IGNORANTIA_CONTACT_EMAIL` no ambiente.
2. **Resolução de título via wbsearchentities**: antes exigia título exato.
   Agora resolve via Wikidata + sitelinks.
3. **Erros propagados**: antes engolia erros silenciosamente. Agora emite
   `WikimediaFetchWarning` e popula `self.fetch_errors`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

VERSION = "2.23.0"
DEFAULT_TIMEOUT = 30.0
DEFAULT_THROTTLE = 1.0


WIKIPEDIA_REST_BASE = "https://{lang}.wikipedia.org/api/rest_v1"
WIKIPEDIA_API_BASE = "https://{lang}.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"


class WikimediaFetchWarning(UserWarning):
    """Warning emitido quando uma chamada à Wikipedia/Wikidata falha."""


def _build_user_agent(contact_email: str | None = None) -> str:
    """Constrói User-Agent compliant com política Wikimedia.

    Política: https://api.wikimedia.org/wiki/Documentation/Conventions/User-Agent_policy
    Formato: `<tool>/<version> (<contact>) <library>`.
    """
    contact = contact_email or os.environ.get("IGNORANTIA_CONTACT_EMAIL")
    if not contact:
        contact = "https://github.com/anthropics/ignorantia (no-contact-email-set)"
    return (f"ignorantia-skill/{VERSION} ({contact}) "
            f"python-urllib/{sys.version_info.major}.{sys.version_info.minor}")


@dataclass
class WikipediaSnippet:
    title: str
    extract: str
    url: str
    language: str
    accessed_at: str

    def to_citation(self) -> str:
        return f"(WIKIPEDIA, \"{self.title}\", acesso em {self.accessed_at})"

    def to_html_link(self) -> str:
        cite = self.to_citation()
        return f'<a href="{self.url}" target="_blank" rel="noopener">{cite}</a>'


@dataclass
class WikidataEntity:
    qid: str
    label: str
    description: str
    url: str
    accessed_at: str
    instance_of: list[str] = field(default_factory=list)
    sitelink_to_wikipedia: str | None = None

    def to_citation(self) -> str:
        return (f"(WIKIDATA {self.qid}, \"{self.label}\", "
                f"acesso em {self.accessed_at})")

    def to_html_link(self) -> str:
        cite = self.to_citation()
        return f'<a href="{self.url}" target="_blank" rel="noopener">{cite}</a>'


class ContextualPreamble:
    """Gerador da seção 'O campo onde este artigo vive' (DD-11)."""

    AREA_TO_DISCIPLINE_MAP = {
        "saude": ["Medicina", "Saúde pública", "Health sciences"],
        "educacao": ["Educação", "Pedagogia", "Education"],
        "cs_se": ["Ciência da computação", "Engenharia de software",
                   "Computer science"],
        "ciencias_sociais": ["Ciências sociais", "Sociologia",
                              "Social sciences"],
        "humanidades": ["Humanidades", "Filosofia", "Humanities"],
        "business": ["Administração", "Management", "Business administration"],
        "multi": ["Ciência interdisciplinar", "Interdisciplinary science"],
    }

    def __init__(self, language: str = "pt-BR",
                 contact_email: str | None = None,
                 throttle: float = DEFAULT_THROTTLE,
                 timeout: float = DEFAULT_TIMEOUT):
        self.language = language
        self.lang_code = self._lang_to_code(language)
        self.throttle = throttle
        self.timeout = timeout
        self.user_agent = _build_user_agent(contact_email)
        self.topic: str = ""
        self.area: str = "multi"
        self.wikipedia_snippets: list[WikipediaSnippet] = []
        self.wikidata_entities: list[WikidataEntity] = []
        self.accessed_at = date.today().isoformat()
        self.fetch_errors: list[dict] = []  # F1: erros propagados

    def _lang_to_code(self, language: str) -> str:
        return language.split("-")[0].lower()

    def set_topic(self, topic: str, area: str = "multi") -> None:
        self.topic = topic
        self.area = area if area in self.AREA_TO_DISCIPLINE_MAP else "multi"

    def _http_get_json(self, url: str, label: str = "request") -> dict | None:
        """GET. F1: propaga erros via warnings + self.fetch_errors."""
        if self.throttle > 0:
            time.sleep(self.throttle)
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err = {"label": label, "url": url, "status": exc.code,
                   "reason": str(exc.reason)}
            self.fetch_errors.append(err)
            warnings.warn(
                f"Wikimedia fetch failed: {label} → HTTP {exc.code} {exc.reason}",
                category=WikimediaFetchWarning, stacklevel=2,
            )
            return None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            err = {"label": label, "url": url, "error": str(exc)}
            self.fetch_errors.append(err)
            warnings.warn(
                f"Wikimedia fetch failed: {label} → {exc}",
                category=WikimediaFetchWarning, stacklevel=2,
            )
            return None

    def _resolve_term_via_wikidata(self, term: str) -> tuple[str, str] | None:
        """Resolve termo arbitrário para (wikidata_qid, wikipedia_title) via
        wbsearchentities + sitelinks. F1."""
        params = {
            "action": "wbsearchentities",
            "search": term,
            "language": self.lang_code,
            "format": "json",
            "limit": 1,
        }
        url = f"{WIKIDATA_API}?{urllib.parse.urlencode(params)}"
        data = self._http_get_json(url, label=f"wbsearch:{term}")
        if not data or not data.get("search"):
            return None

        qid = data["search"][0].get("id", "")
        if not qid.startswith("Q"):
            return None

        params2 = {
            "action": "wbgetentities",
            "ids": qid,
            "props": "sitelinks",
            "sitefilter": f"{self.lang_code}wiki",
            "format": "json",
        }
        url2 = f"{WIKIDATA_API}?{urllib.parse.urlencode(params2)}"
        data2 = self._http_get_json(url2, label=f"wbgetentities:{qid}")
        if not data2:
            return (qid, term)

        sitelinks = (data2.get("entities", {}).get(qid, {}).get("sitelinks") or {})
        wiki_key = f"{self.lang_code}wiki"
        if wiki_key in sitelinks:
            return (qid, sitelinks[wiki_key].get("title", term))
        return (qid, term)

    def fetch_wikipedia_context(self, max_articles: int = 4) -> int:
        """Busca artigos da Wikipedia. F1: resolve título via Wikidata."""
        if not self.topic:
            return 0

        terms = [self.topic] + self.AREA_TO_DISCIPLINE_MAP.get(
            self.area, ["Ciência"]
        )[:2]
        seen_titles: set = set()

        for term in terms[:max_articles]:
            resolved = self._resolve_term_via_wikidata(term)
            page_title = resolved[1] if resolved else term

            base_url = WIKIPEDIA_REST_BASE.format(lang=self.lang_code)
            encoded = urllib.parse.quote(page_title.replace(" ", "_"), safe="")
            url = f"{base_url}/page/summary/{encoded}"
            data = self._http_get_json(url, label=f"summary:{page_title}")
            if not data or "extract" not in data:
                continue

            title = data.get("title", page_title)
            if title in seen_titles:
                continue
            seen_titles.add(title)

            page_url = (
                (data.get("content_urls", {}) or {})
                .get("desktop", {})
                .get("page",
                     f"https://{self.lang_code}.wikipedia.org/wiki/"
                     f"{urllib.parse.quote(title.replace(' ', '_'))}")
            )
            self.wikipedia_snippets.append(WikipediaSnippet(
                title=title,
                extract=data.get("extract", "")[:600],
                url=page_url,
                language=self.lang_code,
                accessed_at=self.accessed_at,
            ))
        return len(self.wikipedia_snippets)

    def fetch_wikidata_entities(self, max_entities: int = 3) -> int:
        if not self.topic:
            return 0
        params = {
            "action": "wbsearchentities",
            "search": self.topic,
            "language": self.lang_code,
            "format": "json",
            "limit": max_entities,
        }
        url = f"{WIKIDATA_API}?{urllib.parse.urlencode(params)}"
        data = self._http_get_json(url, label="wbsearch:topic")
        if not data or "search" not in data:
            return 0

        for hit in data["search"][:max_entities]:
            qid = hit.get("id", "")
            if not qid.startswith("Q"):
                continue
            self.wikidata_entities.append(WikidataEntity(
                qid=qid,
                label=hit.get("label", ""),
                description=hit.get("description", ""),
                url=f"https://www.wikidata.org/wiki/{qid}",
                accessed_at=self.accessed_at,
            ))
        return len(self.wikidata_entities)

    def _section_title(self) -> str:
        if self.lang_code == "en":
            return "The field where this article lives"
        if self.lang_code == "es":
            return "El campo donde vive este artículo"
        return "O campo onde este artigo vive"

    def render_html(self) -> str:
        title_section = self._section_title()
        html_parts = [
            '<section id="contextual-preamble" class="contextual-preamble">',
            f'  <h2>{title_section}</h2>',
            '  <p class="audience-note">'
            '    <em>Esta seção é uma introdução ao campo de pesquisa para leitores '
            'que não são especialistas. Não substitui a Introdução do trabalho, que '
            'aborda o tema específico desta pesquisa.</em>'
            '  </p>',
        ]

        if not self.wikipedia_snippets and not self.wikidata_entities:
            warning_msg = ('<strong>Nota:</strong> Não foi possível recuperar contexto '
                            'enciclopédico da Wikipedia/Wikidata para este tema.')
            if self.fetch_errors:
                warning_msg += (f' Houve {len(self.fetch_errors)} erro(s) de rede '
                                 f'durante a tentativa.')
            html_parts.append(
                f'  <p class="contextual-warning">{warning_msg}</p>'
            )
        else:
            for snip in self.wikipedia_snippets:
                cite_html = snip.to_html_link()
                html_parts.append(
                    f'  <p class="contextual-paragraph">'
                    f'    {snip.extract} {cite_html}'
                    f'  </p>'
                )

            if self.wikidata_entities:
                html_parts.append(
                    '  <h3>Entidades estruturadas no campo</h3>'
                    '  <ul class="wikidata-entities">'
                )
                for ent in self.wikidata_entities:
                    cite_html = ent.to_html_link()
                    html_parts.append(
                        f'    <li><strong>{ent.label}</strong>: '
                        f'{ent.description} {cite_html}</li>'
                    )
                html_parts.append('  </ul>')

        html_parts.append(
            '  <aside class="references-contextual">'
            '    <h4>Referências contextuais</h4>'
            '    <p><em>As referências abaixo são fontes enciclopédicas usadas '
            'apenas para situar o leitor no campo. Não constituem evidência '
            'científica para a metodologia desta pesquisa.</em></p>'
            '    <ol>'
        )
        for snip in self.wikipedia_snippets:
            html_parts.append(
                f'      <li>WIKIPEDIA. <em>{snip.title}</em>. '
                f'Disponível em: <a href="{snip.url}">{snip.url}</a>. '
                f'Acesso em: {snip.accessed_at}.</li>'
            )
        for ent in self.wikidata_entities:
            html_parts.append(
                f'      <li>WIKIDATA. {ent.qid}: <em>{ent.label}</em>. '
                f'Disponível em: <a href="{ent.url}">{ent.url}</a>. '
                f'Acesso em: {ent.accessed_at}.</li>'
            )
        html_parts.append('    </ol></aside>')
        html_parts.append('</section>')
        return "\n".join(html_parts)

    def render_markdown(self) -> str:
        title_section = self._section_title()
        lines = [
            f"## {title_section}",
            "",
            "*Esta seção é uma introdução ao campo de pesquisa para leitores que não",
            "são especialistas. Não substitui a Introdução do trabalho.*",
            "",
        ]

        if not self.wikipedia_snippets and not self.wikidata_entities:
            msg = ("**Nota:** Não foi possível recuperar contexto enciclopédico "
                   "(Wikipedia/Wikidata) para este tema.")
            if self.fetch_errors:
                msg += f" Houve {len(self.fetch_errors)} erro(s) de rede."
            lines.append(msg)
            lines.append("")
            return "\n".join(lines)

        for snip in self.wikipedia_snippets:
            cite = snip.to_citation()
            lines.append(f"{snip.extract} [{cite}]({snip.url})")
            lines.append("")

        if self.wikidata_entities:
            lines.append("### Entidades estruturadas no campo")
            lines.append("")
            for ent in self.wikidata_entities:
                cite = ent.to_citation()
                lines.append(f"- **{ent.label}**: {ent.description}. "
                              f"[{cite}]({ent.url})")
            lines.append("")

        lines.append("### Referências contextuais")
        lines.append("")
        lines.append(
            "*As referências abaixo são fontes enciclopédicas usadas apenas "
            "para situar o leitor no campo. Não constituem evidência científica.*"
        )
        lines.append("")
        for i, snip in enumerate(self.wikipedia_snippets, 1):
            lines.append(
                f"{i}. WIKIPEDIA. *{snip.title}*. Disponível em: "
                f"<{snip.url}>. Acesso em: {snip.accessed_at}."
            )
        offset = len(self.wikipedia_snippets)
        for j, ent in enumerate(self.wikidata_entities, 1):
            lines.append(
                f"{offset + j}. WIKIDATA. {ent.qid}: *{ent.label}*. Disponível em: "
                f"<{ent.url}>. Acesso em: {ent.accessed_at}."
            )
        lines.append("")
        return "\n".join(lines)

    def render_pptx_slides(self) -> list[dict]:
        title_section = self._section_title()
        slides = []
        intro_text = ("Esta apresentação começa com um panorama do campo "
                      "para audiência ampla. As páginas seguintes mostram "
                      "onde a pesquisa se situa antes de detalhar a metodologia.")
        slides.append({
            "type": "section_header",
            "title": title_section,
            "content": intro_text,
        })

        for snip in self.wikipedia_snippets[:3]:
            slides.append({
                "type": "content",
                "title": snip.title,
                "content": snip.extract,
                "reference": snip.to_citation(),
                "url": snip.url,
            })

        if self.wikidata_entities:
            entity_lines = [f"• {e.label}: {e.description}"
                            for e in self.wikidata_entities]
            slides.append({
                "type": "content",
                "title": "Entidades estruturadas no campo",
                "content": "\n".join(entity_lines),
                "references": [e.to_citation() for e in self.wikidata_entities],
                "urls": [e.url for e in self.wikidata_entities],
            })
        return slides

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "area": self.area,
            "language": self.language,
            "accessed_at": self.accessed_at,
            "user_agent": self.user_agent,
            "wikipedia_snippets": [
                {"title": s.title, "extract": s.extract, "url": s.url,
                 "language": s.language, "accessed_at": s.accessed_at}
                for s in self.wikipedia_snippets
            ],
            "wikidata_entities": [
                {"qid": e.qid, "label": e.label, "description": e.description,
                 "url": e.url, "accessed_at": e.accessed_at}
                for e in self.wikidata_entities
            ],
            "fetch_errors": self.fetch_errors,
            "note": ("Preâmbulo contextual gerado via Wikipedia + Wikidata. "
                     "Fonte acessória; não constitui evidência científica para "
                     "a metodologia. Distinto da Introdução do paper (DD-11)."),
        }


def _mock_preamble(topic: str, area: str = "multi", language: str = "pt-BR"
                   ) -> ContextualPreamble:
    cp = ContextualPreamble(language=language)
    cp.set_topic(topic, area=area)
    cp.wikipedia_snippets = [
        WikipediaSnippet(
            title="[mock] Educação",
            extract=("Educação é o conjunto de processos formativos que se "
                     "desenvolvem na vida familiar, na convivência humana, no "
                     "trabalho, nas instituições de ensino e pesquisa, nos "
                     "movimentos sociais e organizações da sociedade civil "
                     "e nas manifestações culturais."),
            url=f"https://{cp.lang_code}.wikipedia.org/wiki/Educa%C3%A7%C3%A3o",
            language=cp.lang_code, accessed_at=cp.accessed_at,
        ),
        WikipediaSnippet(
            title="[mock] Letramento digital",
            extract=("Letramento digital é a capacidade de uma pessoa de "
                     "compreender e utilizar tecnologias digitais para acessar, "
                     "criar, comunicar e participar em práticas sociais."),
            url=f"https://{cp.lang_code}.wikipedia.org/wiki/Letramento_digital",
            language=cp.lang_code, accessed_at=cp.accessed_at,
        ),
    ]
    cp.wikidata_entities = [
        WikidataEntity(
            qid="Q8434",
            label="[mock] educação",
            description="processo de facilitação da aprendizagem",
            url="https://www.wikidata.org/wiki/Q8434",
            accessed_at=cp.accessed_at,
        ),
    ]
    return cp


def _cli() -> int:
    p = argparse.ArgumentParser(
        description="Gera preâmbulo contextual via Wikipedia + Wikidata (DD-11).")
    p.add_argument("--topic", required=True)
    p.add_argument("--area", default="multi",
                   choices=list(ContextualPreamble.AREA_TO_DISCIPLINE_MAP.keys()))
    p.add_argument("--language", default="pt-BR")
    p.add_argument("--contact-email", default=None,
                   help="Email para User-Agent Wikimedia. "
                         "Lê IGNORANTIA_CONTACT_EMAIL do ambiente.")
    p.add_argument("--mock", action="store_true")
    p.add_argument("--format", choices=["html", "markdown", "json", "pptx"],
                   default="html")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    if args.mock:
        cp = _mock_preamble(args.topic, args.area, args.language)
    else:
        cp = ContextualPreamble(language=args.language,
                                contact_email=args.contact_email)
        cp.set_topic(args.topic, area=args.area)
        n_wiki = cp.fetch_wikipedia_context()
        n_wd = cp.fetch_wikidata_entities()
        print(f"[preamble] {n_wiki} Wikipedia + {n_wd} Wikidata.",
              file=sys.stderr)
        if cp.fetch_errors:
            print(f"[preamble] {len(cp.fetch_errors)} fetch error(s); "
                  "ver fetch_errors em --format json.", file=sys.stderr)

    out_path = Path(args.output)
    if args.format == "html":
        out_path.write_text(cp.render_html(), encoding="utf-8")
    elif args.format == "markdown":
        out_path.write_text(cp.render_markdown(), encoding="utf-8")
    elif args.format == "json":
        out_path.write_text(json.dumps(cp.to_dict(), indent=2,
                                        ensure_ascii=False), encoding="utf-8")
    elif args.format == "pptx":
        slides_data = {
            "topic": cp.topic, "area": cp.area, "language": cp.language,
            "slides": cp.render_pptx_slides(),
        }
        out_path.write_text(json.dumps(slides_data, indent=2,
                                        ensure_ascii=False), encoding="utf-8")

    print(f"[preamble] {args.format} → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
