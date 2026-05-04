"""_skill_version.py — Constante única de versão do skill (E2, v2.23.0).

Antes da v2.23.0, USER_AGENT era hardcoded em 10 valores diferentes nos adapters:
    "ignorantia-skill/2.6.0"
    "ignorantia-skill/2.9.0"
    "ignorantia-skill/2.10.0"
    "ignorantia-skill/2.10.1"
    "ignorantia-skill/2.10.2"
    "ignorantia-skill/2.11.0"
    "ignorantia-skill/2.12.0"
    ...

Cada adapter fossilizava uma versão antiga. DRY violation grave: alterar versão
exigia editar todos os arquivos.

Solução: single source of truth para versão do skill. Adapters importam VERSION
ou usam build_user_agent() e ficam sempre sincronizados.

Uso:
    from _skill_version import VERSION, build_user_agent
    USER_AGENT = build_user_agent()  # módulo nível
    # ou em request:
    headers = {"User-Agent": build_user_agent("contato@institucao.org")}
"""
import os
import sys

VERSION = "2.23.0"


def build_user_agent(contact_email: str | None = None) -> str:
    """Retorna User-Agent compliant com Wikimedia/Crossref recomendações.

    Wikimedia: https://meta.wikimedia.org/wiki/User-Agent_policy
    Crossref polite pool: incluir email opcional.

    Args:
        contact_email: opcional, email institucional para polite pool.
            Se None, lê IGNORANTIA_CONTACT_EMAIL do ambiente.

    Returns:
        String User-Agent no formato:
        "ignorantia-skill/<VERSION> (<email>) python-urllib/<py_version>"
    """
    email = contact_email or os.environ.get("IGNORANTIA_CONTACT_EMAIL")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    base = f"ignorantia-skill/{VERSION}"
    if email:
        return f"{base} ({email}) python-urllib/{py_ver}"
    return f"{base} python-urllib/{py_ver}"
