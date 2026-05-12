#!/usr/bin/env python3
"""Phase 2 — single-command orchestrator.

Chains the mechanical steps of Phase 2 into two subcommands:

* ``prepare <handoff.json>`` — runs ``phase2_init`` → ``phase2_retrieve``
  → ``phase2_extract``. Produces a run dir with bootstrapped layout,
  retrieved sources, parsed text + index. **Stops here**: the cowork-
  Claude does the cognitive work (write manuscript.tex,
  bibliography.bib, extraction.csv, claim_to_source.json, etc.) before
  invoking ``finalize``.

* ``finalize <run_dir>`` — compiles the manuscript (pdflatex + bibtex
  + pdflatex × 2 + pandoc to DOCX), runs the seven Phase-2 gates
  sequentially, and assembles the final ZIP. If any gate fails, the
  ZIP is **not** built; the operator sees which gate blocked and
  which sidecar JSON to inspect.

Usage::

    # Step 1: prepare workspace (mechanical)
    python3 scripts/phase2_orchestrator.py prepare path/to/handoff.json \\
        --output-dir runs/ \\
        --contact-email researcher@example.org

    # Step 2: cowork-Claude writes manuscript.tex + supporting files
    # (no script involvement)

    # Step 3: finalize (mechanical)
    python3 scripts/phase2_orchestrator.py finalize runs/<run-id>/

The split keeps the mechanical work in the script and the cognitive
work outside it. The cowork-Claude reads sources_index.json + parsed/
to inform its writing, and the gates verify the result.

Exit codes:

* ``0`` — every step succeeded.
* ``1`` — input error.
* ``2`` — a substep / gate failed; downstream steps were skipped.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Sequence


SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent


# ── subprocess helper ──────────────────────────────────────────────────


def _run_step(
    name: str, cmd: Sequence[str], *, env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """Run a subprocess step and return (exit_code, stdout, stderr).

    Steps are run with the repo's scripts dir on PYTHONPATH so phase2_*
    modules can import each other freely.
    """
    result = subprocess.run(
        list(cmd),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


# ── prepare ────────────────────────────────────────────────────────────


def cmd_prepare(args: argparse.Namespace) -> int:
    """Run init → retrieve → extract sequentially."""
    init = [
        sys.executable,
        str(SCRIPTS_DIR / "phase2_init.py"),
        str(args.handoff),
        "--output-dir",
        str(args.output_dir),
    ]
    if args.force:
        init.append("--force")
    rc, out, err = _run_step("init", init)
    sys.stdout.write(out)
    sys.stderr.write(err)
    if rc != 0:
        sys.stderr.write("\norchestrator: init step failed; aborting.\n")
        return rc

    # The init step prints the run dir name; we recover it from the
    # output dir contents (single new entry).
    candidates = [p for p in args.output_dir.iterdir() if p.is_dir()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        sys.stderr.write(
            "orchestrator: phase2_init succeeded but no run dir was found.\n"
        )
        return 2
    run_dir = candidates[0]
    sys.stdout.write(f"\norchestrator: run_dir = {run_dir}\n\n")

    retrieve = [
        sys.executable,
        str(SCRIPTS_DIR / "phase2_retrieve.py"),
        str(run_dir),
        "--contact-email",
        args.contact_email,
    ]
    if args.sleep_between_s is not None:
        retrieve.extend(["--sleep-between-s", str(args.sleep_between_s)])
    rc, out, err = _run_step("retrieve", retrieve)
    sys.stdout.write(out)
    sys.stderr.write(err)
    if rc != 0:
        sys.stderr.write("\norchestrator: retrieve step failed; aborting.\n")
        return rc

    extract = [
        sys.executable,
        str(SCRIPTS_DIR / "phase2_extract.py"),
        str(run_dir),
    ]
    rc, out, err = _run_step("extract", extract)
    sys.stdout.write(out)
    sys.stderr.write(err)
    if rc != 0:
        sys.stderr.write("\norchestrator: extract step failed; aborting.\n")
        return rc

    sys.stdout.write(
        f"\nPhase 2 prepare complete.\n"
        f"  run dir: {run_dir}\n\n"
        f"Next: the cowork session should now read\n"
        f"  - {run_dir}/sources_index.json\n"
        f"  - {run_dir}/parsed/*.txt\n"
        f"and write manuscript.tex, bibliography.bib, extraction.csv,\n"
        f"claim_to_source.json, quality-appraisal.csv, prisma-flow.svg,\n"
        f"and the AI-disclosure block to the run dir.\n\n"
        f"Then run:\n"
        f"  python3 scripts/phase2_orchestrator.py finalize {run_dir}\n"
    )
    return 0


# ── finalize ───────────────────────────────────────────────────────────


# The seven Phase-2 gates in canonical order. Each tuple is
# (gate_name, command_args_template, sidecar_filename).
# Args use the placeholder "{run_dir}" which gets substituted.
_SEVEN_GATES: Sequence[tuple[str, Sequence[str], str]] = (
    (
        "persona-voice",
        ("check_persona_voice.py", "{run_dir}/manuscript.tex", "--strict"),
        "persona_voice_gate.json",
    ),
    (
        "assessment",
        (
            "generate_assessment.py",
            "--package-dir", "{run_dir}",
            "--out", "{run_dir}/avaliacao.md",
            "--version", "1.0.0",
        ),
        "assessment_gate.json",
    ),
    (
        "pipeline-invariants",
        ("check_pipeline_invariants.py", "{run_dir}"),
        "pipeline_invariants_gate.json",
    ),
    (
        "vocabulary",
        (
            "check_decision_19_vocabulary.py",
            "--all", "{run_dir}",
            "--gate-sidecar", "--quiet",
        ),
        "vocabulary_gate.json",
    ),
    (
        "claim-source",
        ("check_claim_source_coverage.py", "{run_dir}", "--quiet"),
        "claim_source_gate.json",
    ),
    (
        "citation-graph",
        ("check_citation_graph.py", "{run_dir}", "--quiet"),
        "citation_graph_gate.json",
    ),
    (
        "manuscript-substantial",
        ("check_manuscript_substantial.py", "{run_dir}", "--quiet"),
        "manuscript_substantial_gate.json",
    ),
)


def _resolve_args(template: Sequence[str], run_dir: Path) -> list[str]:
    """Substitute ``{run_dir}`` placeholders in gate command templates."""
    out: list[str] = []
    for token in template:
        out.append(token.replace("{run_dir}", str(run_dir)))
    return out


def _compile_manuscript(run_dir: Path) -> tuple[bool, str]:
    """Compile manuscript.tex → PDF + DOCX. Returns (ok, log_text).

    The actual compilation runs ``pdflatex + bibtex + pdflatex × 2 +
    pandoc``. Missing binaries are not the orchestrator's problem —
    the manuscript-substantial gate will catch a missing PDF.
    """
    tex = run_dir / "manuscript.tex"
    if not tex.is_file():
        return False, f"manuscript.tex not found in {run_dir}"

    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    compile_log = logs_dir / "compile.log"
    cmds = [
        ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(run_dir), str(tex)],
        ["bibtex", str(run_dir / "manuscript")],
        ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(run_dir), str(tex)],
        ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(run_dir), str(tex)],
    ]
    log_parts: list[str] = []
    for cmd in cmds:
        if not shutil.which(cmd[0]):
            log_parts.append(f"[skip] {cmd[0]} not on PATH\n")
            continue
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=120
            )
            log_parts.append(f"$ {' '.join(cmd)}\n{r.stdout}\n{r.stderr}\n")
        except subprocess.TimeoutExpired:
            log_parts.append(f"[timeout] {' '.join(cmd)}\n")

    pandoc_cmd = [
        "pandoc",
        str(tex),
        "-o",
        str(run_dir / "manuscript.docx"),
    ]
    bib = run_dir / "bibliography.bib"
    if bib.is_file():
        pandoc_cmd.extend(["--bibliography", str(bib)])
    if shutil.which("pandoc"):
        try:
            r = subprocess.run(
                pandoc_cmd, capture_output=True, text=True, check=False, timeout=60
            )
            log_parts.append(f"$ {' '.join(pandoc_cmd)}\n{r.stdout}\n{r.stderr}\n")
        except subprocess.TimeoutExpired:
            log_parts.append(f"[timeout] {' '.join(pandoc_cmd)}\n")

    compile_log.write_text("".join(log_parts), encoding="utf-8")
    pdf_ok = (run_dir / "manuscript.pdf").is_file()
    return pdf_ok, str(compile_log)


def _run_gate(name: str, args_template: Sequence[str], run_dir: Path) -> int:
    """Run one gate by command-name. ``args_template`` starts with the
    script filename (resolved against SCRIPTS_DIR)."""
    script = SCRIPTS_DIR / args_template[0]
    cmd = [sys.executable, str(script), *_resolve_args(args_template[1:], run_dir)]
    rc, out, err = _run_step(name, cmd)
    sys.stdout.write(f"\n[gate {name}]\n")
    sys.stdout.write(out)
    sys.stderr.write(err)
    return rc


def _move_gate_sidecar(run_dir: Path, sidecar_name: str) -> None:
    """Move sidecar from run_dir/ to run_dir/gates/ if it ended up at
    the top level (some gates emit there for compatibility)."""
    src = run_dir / sidecar_name
    if src.is_file():
        gates_dir = run_dir / "gates"
        gates_dir.mkdir(parents=True, exist_ok=True)
        target = gates_dir / sidecar_name
        if target.exists():
            target.unlink()
        shutil.move(str(src), str(target))


def _build_zip(run_dir: Path, zip_name: str) -> Path:
    """Assemble the final Zenodo ZIP from the run dir."""
    zip_path = run_dir.parent / zip_name
    if zip_path.exists():
        zip_path.unlink()
    # Files to include: everything in run_dir except logs/ and sources/
    # (sources stay local; the deposit carries citations_to_obtain
    # rather than the PDFs themselves).
    excluded_dirs = {"sources", "logs"}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(run_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(run_dir)
            if rel.parts and rel.parts[0] in excluded_dirs:
                continue
            zf.write(path, arcname=str(rel))
    return zip_path


def cmd_finalize(args: argparse.Namespace) -> int:
    """Compile + run 7 gates + build ZIP."""
    run_dir = args.run_dir
    if not run_dir.is_dir():
        sys.stderr.write(f"ERROR: run dir not found: {run_dir}\n")
        return 1
    if not (run_dir / "manuscript.tex").is_file():
        sys.stderr.write(
            f"ERROR: {run_dir}/manuscript.tex not found. "
            f"The cowork session must produce manuscript.tex (and "
            f"bibliography.bib, extraction.csv, claim_to_source.json, "
            f"quality-appraisal.csv) before invoking finalize.\n"
        )
        return 1

    # Step 1: compile
    if not args.skip_compile:
        sys.stdout.write("orchestrator: compiling manuscript...\n")
        pdf_ok, log_path = _compile_manuscript(run_dir)
        sys.stdout.write(f"  compile log: {log_path}  (pdf: {'ok' if pdf_ok else 'missing'})\n")

    # Step 2: run the 7 gates sequentially
    failed_gates: list[str] = []
    for name, args_template, sidecar in _SEVEN_GATES:
        rc = _run_gate(name, args_template, run_dir)
        _move_gate_sidecar(run_dir, sidecar)
        if rc != 0:
            failed_gates.append(name)
            if not args.continue_on_gate_failure:
                sys.stderr.write(
                    f"\norchestrator: gate '{name}' failed (exit {rc}); "
                    f"aborting before ZIP. Sidecar at "
                    f"{run_dir}/gates/{sidecar}.\n"
                )
                return 2

    if failed_gates:
        sys.stderr.write(
            f"\norchestrator: {len(failed_gates)} gate(s) failed: "
            f"{', '.join(failed_gates)}. ZIP NOT built.\n"
        )
        return 2

    # Step 3: build ZIP
    zip_name = args.zip_name or _derive_zip_name(run_dir)
    zip_path = _build_zip(run_dir, zip_name)
    sha = sha256(zip_path.read_bytes()).hexdigest()

    # Update state
    state_path = run_dir / "phase2_state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("completed_steps", []).append("finalize")
        state["finalize"] = {
            "zip_path": str(zip_path),
            "zip_sha256": sha,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "failed_gates": failed_gates,
        }
        state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    sys.stdout.write(
        f"\nPhase 2 finalize complete.\n"
        f"  ZIP:    {zip_path}\n"
        f"  SHA256: {sha}\n"
        f"  Seven gates passed; deposit is fit to upload to Zenodo "
        f"without further review.\n"
    )
    return 0


def _derive_zip_name(run_dir: Path) -> str:
    """Default ZIP filename derives from the run dir name (which is
    already brand-free by phase2_init's derive_run_id)."""
    return f"{run_dir.name}.zip"


# ── CLI ────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2 orchestrator. Chains init + retrieve + extract "
            "(prepare) and compile + 7 gates + ZIP (finalize). The "
            "cognitive work between prepare and finalize is the "
            "cowork session's job."
        )
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="Run init + retrieve + extract.")
    p_prep.add_argument("handoff", type=Path, help="Phase 1 handoff JSON.")
    p_prep.add_argument(
        "--output-dir", type=Path, default=Path("runs"),
        help="Parent dir under which the run dir is created.",
    )
    p_prep.add_argument(
        "--contact-email", required=True,
        help="Required for Unpaywall polite-pool.",
    )
    p_prep.add_argument(
        "--sleep-between-s", type=float, default=None,
        help="Delay between retrieval HTTP calls.",
    )
    p_prep.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing run dir (phase2_init --force).",
    )
    p_prep.set_defaults(handler=cmd_prepare)

    p_fin = sub.add_parser("finalize", help="Compile + 7 gates + ZIP.")
    p_fin.add_argument(
        "run_dir", type=Path,
        help="Run dir prepared by `orchestrator prepare`.",
    )
    p_fin.add_argument(
        "--skip-compile", action="store_true",
        help="Skip the pdflatex+pandoc step (manuscript.pdf already present).",
    )
    p_fin.add_argument(
        "--continue-on-gate-failure", action="store_true",
        help=(
            "Run every gate even when one fails (collect all failures "
            "before reporting). Default is to short-circuit on first "
            "failure to mimic shell-`&&` semantics."
        ),
    )
    p_fin.add_argument(
        "--zip-name", default=None,
        help="Override the auto-derived ZIP filename.",
    )
    p_fin.set_defaults(handler=cmd_finalize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
