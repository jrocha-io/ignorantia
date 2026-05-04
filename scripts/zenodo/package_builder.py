"""
ZenodoPackageBuilder — agrega os artefatos obrigatórios do pacote de
reprodutibilidade e produz reproducibility_manifest.yaml com SHA-256.

Convenção de paths:

    package_root/
        prompt.md                     (obrigatório)
        model.txt                     (obrigatório)
        databases.txt                 (obrigatório)
        dois.csv                      (obrigatório)
        selecao_log.json              (obrigatório)
        verificacao_dois.json         (obrigatório — produzido por doi_verifier)
        extraction_log.json           (recomendado)
        ai_disclosure.md              (obrigatório)
        reproducibility_manifest.yaml (gerado por este builder)
        README.md                     (obrigatório)
"""

from __future__ import annotations
import hashlib
import json
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FILES = [
    "prompt.md",
    "model.txt",
    "databases.txt",
    "dois.csv",
    "selecao_log.json",
    "verificacao_dois.json",
    "ai_disclosure.md",
    "README.md",
]
RECOMMENDED_FILES = ["extraction_log.json"]


@dataclass
class FileEntry:
    relative_path: str
    sha256: str
    size_bytes: int
    is_required: bool


@dataclass
class ZenodoPackageManifest:
    package_id: str
    review_type: str  # systematic_review_with_2_reviewers | scoping_review | rapid_review | mapping_study
    review_purpose: str  # design_foundational | design_validation | design_correction | independent_inquiry
    created_iso8601: str
    ignorantia_version: str
    files: list[FileEntry]
    missing_required: list[str] = field(default_factory=list)


class ZenodoPackageBuilder:
    """Orquestra criação do pacote.

    Uso típico:
        b = ZenodoPackageBuilder("/tmp/zenodo_pkg")
        b.add_artifact("prompt.md", source_path="...")
        b.set_metadata(review_type="rapid_review", review_purpose="design_foundational")
        manifest = b.build()
    """

    def __init__(self, package_root: Path | str):
        self.root = Path(package_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._review_type: str | None = None
        self._review_purpose: str | None = None
        self._package_id: str | None = None

    def set_metadata(self, *, review_type: str, review_purpose: str,
                     package_id: str | None = None) -> None:
        valid_types = {
            "systematic_review_with_2_reviewers",
            "systematic_review_strict",
            "scoping_review",
            "rapid_review",
            "mapping_study",
            "meta_analysis",
            "umbrella_review",
            "living_review",
        }
        valid_purposes = {
            "design_foundational",
            "design_validation",
            "design_correction",
            "independent_inquiry",
        }
        if review_type not in valid_types:
            raise ValueError(f"review_type inválido: {review_type}")
        if review_purpose not in valid_purposes:
            raise ValueError(f"review_purpose inválido: {review_purpose}")
        self._review_type = review_type
        self._review_purpose = review_purpose
        if package_id:
            self._package_id = package_id

    def add_artifact(self, target_filename: str, *, source_path: Path | str | None = None,
                     content: str | None = None) -> None:
        target = self.root / target_filename
        if source_path:
            shutil.copy2(source_path, target)
        elif content is not None:
            target.write_text(content, encoding="utf-8")
        else:
            raise ValueError("source_path ou content obrigatório")

    def _sha256(self, p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def build(self, ignorantia_version: str = "2.0.0") -> ZenodoPackageManifest:
        if not self._review_type or not self._review_purpose:
            raise RuntimeError("set_metadata() deve ser chamado antes de build()")

        # Coleta arquivos presentes
        present = {p.name for p in self.root.iterdir() if p.is_file()}
        missing = [f for f in REQUIRED_FILES if f not in present]

        files: list[FileEntry] = []
        for p in sorted(self.root.iterdir()):
            if not p.is_file():
                continue
            if p.name == "reproducibility_manifest.yaml":
                continue  # não inclui o próprio manifest
            files.append(FileEntry(
                relative_path=p.name,
                sha256=self._sha256(p),
                size_bytes=p.stat().st_size,
                is_required=p.name in REQUIRED_FILES,
            ))

        manifest = ZenodoPackageManifest(
            package_id=self._package_id or self.root.name,
            review_type=self._review_type,
            review_purpose=self._review_purpose,
            created_iso8601=datetime.now(timezone.utc).isoformat(),
            ignorantia_version=ignorantia_version,
            files=files,
            missing_required=missing,
        )

        # Escreve manifest YAML manualmente (sem dependência)
        manifest_text = self._render_manifest_yaml(manifest)
        (self.root / "reproducibility_manifest.yaml").write_text(manifest_text, encoding="utf-8")

        return manifest

    def _render_manifest_yaml(self, m: ZenodoPackageManifest) -> str:
        lines = [
            "# ignorantia v2.0 — Zenodo Reproducibility Package Manifest",
            "# Generated automatically. Do not edit by hand.",
            "",
            f"package_id: {m.package_id}",
            f"review_type: {m.review_type}",
            f"review_purpose: {m.review_purpose}",
            f"created_iso8601: {m.created_iso8601}",
            f"ignorantia_version: {m.ignorantia_version}",
            "",
            "files:",
        ]
        for f in m.files:
            lines.append(f"  - relative_path: {f.relative_path}")
            lines.append(f"    sha256: {f.sha256}")
            lines.append(f"    size_bytes: {f.size_bytes}")
            lines.append(f"    is_required: {str(f.is_required).lower()}")
        if m.missing_required:
            lines.append("")
            lines.append("missing_required:")
            for fname in m.missing_required:
                lines.append(f"  - {fname}")
        else:
            lines.append("")
            lines.append("missing_required: []")
        return "\n".join(lines) + "\n"
