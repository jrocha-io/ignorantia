"""
ignorantia v2.0 — Zenodo Reproducibility Package Generator

Gera o pacote obrigatório de reprodutibilidade que acompanha cada SLR/Scoping/Rapid
Review depositada no Zenodo:

  prompt.md                    # Prompt completo de cada fase
  model.txt                    # Provider, modelo, versão, temperatura, top_p, seed
  databases.txt                # Bases + queries + datas
  dois.csv                     # DOIs antes da filtragem
  selecao_log.json             # Inclusões/exclusões com critério
  verificacao_dois.json        # Cross-check Crossref + Retraction Watch + OpenAlex
  extraction_log.json          # Cada extração: prompt, output
  ai_disclosure.md             # Declaração ICMJE/IEEE-compliant
  reproducibility_manifest.yaml # SHA-256 de cada arquivo
  README.md                    # Instruções para reproduzir
"""

__version__ = "2.0.0"

from .package_builder import ZenodoPackageBuilder, ZenodoPackageManifest
from .doi_verifier import verify_dois, DOIVerificationResult

__all__ = [
    "ZenodoPackageBuilder",
    "ZenodoPackageManifest",
    "verify_dois",
    "DOIVerificationResult",
]
