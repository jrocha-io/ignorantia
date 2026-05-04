#!/usr/bin/env python3
"""
_adapter_base.py — Template arquitetural para adapters de bases pagas (DD-8).

Cada adapter de base paywall herda de `PaywallAdapter` e implementa apenas o que é
específico do publisher: endpoint, parser, schema. A cascata de mecanismos legais
(KEY → PROXY → FALLBACK_MD → MOCK) é inteiramente gerenciada pela classe base.

Princípios (DD-6, DD-7, DD-8):
- ToS de plataforma é restrição absoluta. Adapter NUNCA bypassa proteções.
- Cascata é tentada em ordem; nunca pula uma etapa para o fallback.
- Logs em duas camadas (DD-10): este módulo gera Camada 1 (fetched/kept/discarded_local).
- Honestidade declarativa: se não consegue, declara, com razão técnica.

Uso típico em adapter concreto:

    from _adapter_base import PaywallAdapter, AdapterResult

    class ScopusAdapter(PaywallAdapter):
        SOURCE_NAME = "scopus_full"
        SOURCE_TIER = 2

        def _key_endpoint(self) -> str:
            return "https://api.elsevier.com/content/search/scopus"

        def _key_search(self, query, year_start, year_end, max_results, api_key):
            ...
            return AdapterResult(...)

        def _proxy_search(self, query, year_start, year_end, max_results, proxy_host):
            ...

        def _mock(self, query, year_start, year_end):
            ...
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import sys as _sys_ab
from pathlib import Path as _Path_ab
_sys_ab.path.insert(0, str(_Path_ab(__file__).parent.parent))
from _skill_version import VERSION as _SKILL_VERSION_AB

USER_AGENT = f"ignorantia-skill/{_SKILL_VERSION_AB}"
DEFAULT_THROTTLE = 1.0
DEFAULT_TIMEOUT = 30.0


class AdapterMethod(str, Enum):
    """E6 (v2.23.0, auditoria #5): enum canônico para field 'method' nos
    JSON outputs.

    Antes da v2.23.0, 'method' era magic string com 41+ valores ad-hoc
    ('BDTD_REAL_PARTIAL', 'DOAJ_MOCK', 'CROSSREF_REAL_ERROR' etc.).
    Adapters convencionavam o sufixo do source_name + status.

    A partir da v2.23.0, status é um destes 4 valores:
        MOCK         — fixture determinística (CI/offline)
        REAL         — busca real bem-sucedida com parser estruturado
        REAL_PARTIAL — busca real retornou raw bytes mas sem parser
        REAL_ERROR   — busca real falhou (HTTP error, timeout, etc.)

    Adapters podem usar prefixos de fonte (BDTD_REAL_PARTIAL = AdapterMethod.REAL_PARTIAL
    com prefixo); recomendado migrar para enum-only ao longo do tempo.

    Herda de str para serialização JSON natural (`json.dumps` aceita).
    """
    MOCK = "MOCK"
    REAL = "REAL"
    REAL_PARTIAL = "REAL_PARTIAL"
    REAL_ERROR = "REAL_ERROR"

    @classmethod
    def from_string(cls, value: str) -> "AdapterMethod":
        """Mapeia string legada (ex 'BDTD_REAL_PARTIAL') ao enum.

        Estratégia: extrai sufixo após último underscore. Se sufixo desconhecido,
        retorna REAL_PARTIAL como fallback honesto (sem parser implícito).
        """
        if not value:
            return cls.REAL_PARTIAL
        upper = value.upper()
        for method in cls:
            if upper.endswith(f"_{method.value}") or upper == method.value:
                return method
        return cls.REAL_PARTIAL

def cli_exit_with_error_message(result_dict: dict, source_name: str) -> int:
    """D5 (v2.23.0, auditoria #5): helper que imprime mensagem de erro em
    stderr antes de retornar exit code != 0.

    Antes da v2.23.0, adapters usavam o pattern `return 0 if not r.get("error") else 1`
    sem `print(error, file=sys.stderr)`. Resultado: orquestrador mostrava
    `[warn] X — erro:` com mensagem VAZIA. A7 (v2.20.0) corrigiu grey_lit;
    D5 generaliza a todos os adapters.

    Uso:
        return cli_exit_with_error_message(r, "eric")

    Retorna: 0 se sem erro; 1 se erro (após imprimir mensagem em stderr).
    """
    import sys
    error = result_dict.get("error")
    if error:
        print(f"[{source_name}] error: {error}", file=sys.stderr)
        return 1
    return 0


@dataclass
class AdapterResult:
    """Resultado padronizado de uma busca via adapter (com cascata)."""
    source: str
    source_tier: str  # E1 (v2.23.0): string canônica ("tier0"|"tier1"|"tier2"|"tier3")
    method: str  # KEY_REAL | PROXY_REAL | FALLBACK_MD | MOCK | *_ERROR | *_PARTIAL
    query: str
    year_start: int = 0
    year_end: int = 0
    total_results: int = 0
    results: list[dict] = field(default_factory=list)
    error: str | None = None
    note: str | None = None
    fallback_md_path: str | None = None
    log_camada1: dict = field(default_factory=dict)  # DD-10 Camada 1

    def to_dict(self) -> dict:
        d = asdict(self)
        d = {k: v for k, v in d.items() if v is not None and v != [] and v != {}}
        return d


@dataclass
class FetchedItem:
    """Item bibliográfico retornado por um adapter, normalizado."""
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    issn: str | None = None
    isbn: str | None = None
    venue: str | None = None
    language: str = "en"
    is_oa: bool = False
    url: str | None = None
    url_for_pdf: str | None = None
    abstract: str = ""
    publication_type: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, "", [], {})}


class LocalFilter:
    """Filtros locais aplicáveis genericamente sobre items de qualquer adapter.

    Camada 1 dos logs (DD-10): registra quantos foram fetched, quantos sobreviveram,
    quantos foram descartados localmente e por qual razão técnica.
    """

    def __init__(self, year_start: int, year_end: int,
                 accepted_languages: list[str] | None = None,
                 require_doi: bool = False):
        self.year_start = year_start
        self.year_end = year_end
        self.accepted_languages = accepted_languages
        self.require_doi = require_doi
        self.discarded_reasons: dict[str, int] = {}
        self.discarded_items: list[dict] = []

    def apply(self, items: list[FetchedItem]) -> list[FetchedItem]:
        kept = []
        for it in items:
            reason = self._reject_reason(it)
            if reason is None:
                kept.append(it)
            else:
                self.discarded_reasons[reason] = self.discarded_reasons.get(reason, 0) + 1
                self.discarded_items.append({
                    "title": it.title,
                    "doi": it.doi,
                    "year": it.year,
                    "language": it.language,
                    "reason": reason,
                })
        return kept

    def _reject_reason(self, item: FetchedItem) -> str | None:
        if self.year_start and self.year_end and item.year:
            if item.year < self.year_start or item.year > self.year_end:
                return "out_of_temporal_window"
        if self.accepted_languages and item.language:
            if item.language not in self.accepted_languages:
                return "language_not_accepted"
        if self.require_doi and not item.doi:
            return "missing_doi"
        return None

    def to_log_camada1(self, fetched_n: int, kept_n: int) -> dict:
        return {
            "event": "local_filter_applied",
            "fetched": fetched_n,
            "kept_after_local_filter": kept_n,
            "discarded_local": fetched_n - kept_n,
            "discarded_reasons": self.discarded_reasons,
        }


class PaywallAdapter(ABC):
    """Classe base para adapters de bases pagas com cascata de mecanismos legais.

    Subclasses devem definir:
      - `SOURCE_NAME`: nome curto (ex.: "scopus_full")
      - `SOURCE_TIER`: 1 ou 2 conforme política Tier
      - `KEY_ENV_VAR`: nome da variável de ambiente para a chave de API
      - `_key_search()`: implementa busca via API oficial
      - `_proxy_search()`: implementa busca via proxy institucional (opcional;
         pode retornar None se não suportado)
      - `_mock()`: fixture determinística

    A classe gerencia a cascata, fallback .md e logs.
    """

    SOURCE_NAME: str = "paywall_base"
    # E1 (v2.23.0, auditoria #5): SOURCE_TIER agora é STRING canônica
    # ('tier1', 'tier2', 'tier3') para paridade com adapters legacy/retrofitted.
    # Antes da v2.23.0, paywall usava int (2) e retrofitted usava str ('tier2'),
    # causando Liskov violation: pós-processadores quebravam silenciosamente
    # quando comparavam adapters de categorias diferentes.
    SOURCE_TIER: str = "tier2"
    KEY_ENV_VAR: str = "IGNORANTIA_GENERIC_KEY"
    DEFAULT_PROXY_ENV_VAR: str = "IGNORANTIA_PROXY_HOST"

    @abstractmethod
    def _key_search(self, query: str, year_start: int, year_end: int,
                    max_results: int, api_key: str,
                    throttle: float, timeout: float) -> AdapterResult | None:
        ...

    def _proxy_search(self, query: str, year_start: int, year_end: int,
                      max_results: int, proxy_host: str,
                      throttle: float, timeout: float) -> AdapterResult | None:
        """Default: proxy mode não-suportado (override em subclasse se aplicável)."""
        return None

    @abstractmethod
    def _mock(self, query: str, year_start: int, year_end: int) -> AdapterResult:
        ...

    def _generate_fallback_md(self, query: str, year_start: int, year_end: int,
                               output_dir: Path, related_items: list[FetchedItem] | None
                               ) -> Path:
        """Gera citations_to_obtain.md com lista do que precisa ser baixado manualmente.

        Se `related_items` for fornecido (cruzamento com adapters Tier 2), inclui
        a lista detalhada. Caso contrário, gera template com instruções genéricas.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = output_dir / f"citations_to_obtain_{self.SOURCE_NAME}.md"

        publisher = self.SOURCE_NAME.replace("_full", "").replace("_", " ").title()
        n_items = len(related_items) if related_items else 0

        lines = [
            f"# Citações a obter manualmente — {publisher}",
            "",
            f"**Gerado em:** {datetime.now(timezone.utc).isoformat()}Z",
            f"**Query original:** `{query}`",
            f"**Janela temporal:** {year_start}-{year_end}",
            f"**Itens previamente identificados via outros adapters:** {n_items}",
            "",
            f"Esta lista foi gerada porque a busca automática em **{publisher}** não foi possível",
            "sem credencial. Para obter os full-texts, você precisa **uma das opções abaixo**.",
            "",
            "## Opção 1 — Via Periódicos CAPES (CAFe)",
            "",
            "Se você é vinculado a uma IES brasileira:",
            "",
            "1. Acesse <https://www-periodicos-capes-gov-br.ezl.periodicos.capes.gov.br/>",
            "2. Faça login via CAFe com suas credenciais institucionais",
            f"3. Busque cada item da lista abaixo em **{publisher}**",
            "",
            "## Opção 2 — Via biblioteca da sua instituição",
            "",
            "Se sua IES tem assinatura institucional direta com o publisher:",
            "",
            f"1. Acesse o portal da biblioteca da sua IES e procure {publisher}",
            "2. Use o proxy institucional (geralmente `ezproxy.suaies.edu.br` ou similar)",
            "3. Após autenticação, busque cada item da lista abaixo",
            "",
            "## Opção 3 — Via contato com autor correspondente",
            "",
            "Se as opções 1 e 2 não funcionam, o autor correspondente frequentemente envia",
            "PDF gratuitamente quando contatado por e-mail acadêmico.",
            "",
            "## Opção 4 — Solicitação interbibliotecária (COMUT)",
            "",
            "Para itens críticos, sua biblioteca pode solicitar via COMUT (Programa de",
            "Comutação Bibliográfica) da CAPES.",
            "",
            "---",
            "",
            "## Itens identificados via cross-search (outros adapters)",
            "",
        ]

        if related_items:
            lines.append("| # | Título | Autores | Ano | DOI | ISSN/ISBN | Venue |")
            lines.append("|---|---|---|---|---|---|---|")
            for i, it in enumerate(related_items, 1):
                authors = ", ".join(it.authors[:3]) + (" et al." if len(it.authors) > 3 else "")
                ident = it.issn or it.isbn or "-"
                doi_link = f"[{it.doi}](https://doi.org/{it.doi})" if it.doi else "-"
                lines.append(f"| {i} | {it.title or '-'} | {authors or '-'} | "
                             f"{it.year or '-'} | {doi_link} | {ident} | {it.venue or '-'} |")
        else:
            lines.append(f"_Nenhum item foi identificado via outros adapters como pertencente a "
                         f"{publisher} para a query e janela informadas. Use a query "
                         f"`{query}` diretamente nos canais 1-4 acima._")

        lines.extend([
            "",
            "---",
            "",
            "## Notas para reprodutibilidade",
            "",
            "- Este arquivo foi gerado automaticamente pela skill ignorantia.",
            f"- A não-execução automática em **{publisher}** é declarada honestamente "
            "no `manifest.yaml` da revisão.",
            f"- Cite no PRISMA flow diagram que **{publisher}** foi consultado via",
            "  obtenção manual e quantos itens vieram dessa fonte.",
            "",
        ])

        fallback_path.write_text("\n".join(lines), encoding="utf-8")
        return fallback_path

    def _try_cascade(self, query: str, year_start: int, year_end: int,
                     max_results: int, api_key: str | None, proxy_host: str | None,
                     output_dir: Path | None,
                     related_items: list[FetchedItem] | None,
                     throttle: float, timeout: float) -> AdapterResult:
        """Executa cascata KEY → PROXY → FALLBACK_MD."""
        log_attempts = []

        # 1. KEY mode
        if api_key:
            log_attempts.append("KEY_attempted")
            try:
                r = self._key_search(query, year_start, year_end, max_results,
                                     api_key, throttle, timeout)
                if r and not r.error and r.results:
                    r.log_camada1["cascade_attempts"] = log_attempts
                    return r
                if r and r.error:
                    log_attempts.append(f"KEY_error: {r.error[:80]}")
            except Exception as exc:
                log_attempts.append(f"KEY_exception: {str(exc)[:80]}")
        else:
            log_attempts.append("KEY_no_credential")

        # 2. PROXY mode
        if proxy_host:
            log_attempts.append("PROXY_attempted")
            try:
                r = self._proxy_search(query, year_start, year_end, max_results,
                                       proxy_host, throttle, timeout)
                if r and not r.error and r.results:
                    r.log_camada1["cascade_attempts"] = log_attempts
                    return r
                if r and r.error:
                    log_attempts.append(f"PROXY_error: {r.error[:80]}")
                elif r is None:
                    log_attempts.append("PROXY_unsupported")
            except Exception as exc:
                log_attempts.append(f"PROXY_exception: {str(exc)[:80]}")
        else:
            log_attempts.append("PROXY_no_credential")

        # 3. FALLBACK_MD
        out_dir = output_dir or Path.cwd()
        fallback_path = self._generate_fallback_md(query, year_start, year_end,
                                                    out_dir, related_items)
        log_attempts.append(f"FALLBACK_MD_generated: {fallback_path.name}")

        return AdapterResult(
            source=self.SOURCE_NAME,
            source_tier=self.SOURCE_TIER,
            method="FALLBACK_MD",
            query=query, year_start=year_start, year_end=year_end,
            total_results=len(related_items or []),
            results=[],
            note=(f"Acesso programático a {self.SOURCE_NAME} requer credencial. "
                  f"Cascata KEY→PROXY falhou ou não aplicável. Gerado "
                  f"{fallback_path.name} com lista de itens a obter manualmente."),
            fallback_md_path=str(fallback_path),
            log_camada1={"cascade_attempts": log_attempts},
        )

    def search(self, query: str, year_start: int | None = None,
               year_end: int | None = None, max_results: int = 100,
               mock: bool = False,
               api_key: str | None = None, proxy_host: str | None = None,
               output_dir: Path | str | None = None,
               related_items: list[FetchedItem] | None = None,
               throttle: float = DEFAULT_THROTTLE,
               timeout: float = DEFAULT_TIMEOUT) -> dict:
        """Ponto de entrada público. Resolve cascata e retorna dict serializável.

        Args:
            query: query booleana ou termo de busca.
            year_start, year_end: janela temporal.
            max_results: máximo de resultados.
            mock: força modo mock determinístico.
            api_key: se None, lê de env (KEY_ENV_VAR).
            proxy_host: se None, lê de env (DEFAULT_PROXY_ENV_VAR).
            output_dir: diretório onde gravar fallback .md.
            related_items: itens cross-search para popular fallback .md.
        """
        if mock:
            r = self._mock(query, year_start or 0, year_end or 0)
            # F7 (v2.18.1): mock também recebe log_camada1 (consistência de schema
            # com modo real KEY/PROXY/FALLBACK_MD).
            if not r.log_camada1:
                r.log_camada1 = {
                    "event": "local_filter_applied",
                    "fetched": len(r.results),
                    "kept_after_local_filter": len(r.results),
                    "discarded_local": 0,
                    "discarded_reasons": {},
                    "cascade_attempts": ["MOCK_mode"],
                }
            return r.to_dict()

        api_key = api_key or os.environ.get(self.KEY_ENV_VAR)
        proxy_host = proxy_host or os.environ.get(self.DEFAULT_PROXY_ENV_VAR)

        out_dir_path: Path | None = None
        if output_dir is not None:
            out_dir_path = Path(output_dir) if isinstance(output_dir, str) else output_dir

        r = self._try_cascade(
            query, year_start or 0, year_end or 0, max_results,
            api_key, proxy_host, out_dir_path, related_items,
            throttle, timeout,
        )
        return r.to_dict()


def make_cli(adapter_class: type, description: str):
    """Constrói CLI padronizado para um adapter herdeiro de PaywallAdapter."""
    def _cli() -> int:
        p = argparse.ArgumentParser(description=description)
        p.add_argument("--query", required=True)
        p.add_argument("--year-start", type=int)
        p.add_argument("--year-end", type=int)
        p.add_argument("--max-results", type=int, default=100)
        p.add_argument("--api-key", default=None,
                       help=f"API key; lê {adapter_class.KEY_ENV_VAR} do ambiente.")
        p.add_argument("--proxy-host", default=None,
                       help=f"Proxy institucional; lê {adapter_class.DEFAULT_PROXY_ENV_VAR}.")
        p.add_argument("--output-dir", default=".",
                       help="Diretório para fallback citations_to_obtain_*.md.")
        p.add_argument("--mock", action="store_true")
        p.add_argument("--output", required=True)
        args = p.parse_args()
        adapter = adapter_class()
        r = adapter.search(args.query, args.year_start, args.year_end,
                            args.max_results, mock=args.mock,
                            api_key=args.api_key, proxy_host=args.proxy_host,
                            output_dir=args.output_dir)
        Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
        n = r.get("total_results", len(r.get("results", [])))
        method = r.get("method", "?")
        print(f"[{adapter_class.SOURCE_NAME}] method={method} | {n} resultados → {args.output}")
        if r.get("fallback_md_path"):
            print(f"  fallback: {r['fallback_md_path']}")
        if r.get("note"):
            print(f"  nota: {r['note'][:120]}")
        return 0 if not r.get("error") else 1
    return _cli
