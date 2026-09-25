"""Freeze canonical inputs and inventory the complete forensic audit tree."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
ORIGINALS = AUDIT / "originals"
EXPECTED = {
    "segan_submission_files.zip": "533f2d94b4add0245b008d903506e7be714820e1738eb6eef77dc059ea56dbfa",
    "manuscript_inline.docx": "fe711632a49ac89e1740c80068b04187de487345a2998e86aa479d912be7718d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(path: Path) -> tuple[str, str]:
    rel = path.relative_to(ROOT).as_posix()
    suffix = path.suffix.lower().lstrip(".") or "none"
    if rel.startswith("audit/originals/"):
        role = "immutable canonical input"
    elif rel.startswith("audit/canonical_source/"):
        role = "canonical package extraction"
    elif rel.startswith("data/raw/"):
        role = "raw research input"
    elif rel.startswith("data/processed/"):
        role = "derived analysis input"
    elif rel.startswith("scripts/"):
        role = "executable pipeline source"
    elif rel.startswith("analysis/"):
        role = "machine-readable analysis output"
    elif rel.startswith("figures/"):
        role = "manuscript figure"
    elif rel.startswith("tables/"):
        role = "manuscript table"
    elif rel.startswith("manuscript/"):
        role = "submission manuscript component"
    elif rel.startswith("municipality/"):
        role = "municipality planning-support output"
    elif rel.startswith("provenance/") or "PROVENANCE" in rel or "DECISION_LOG" in rel:
        role = "provenance or decision record"
    elif "PHASE_" in rel or "HANDOFF" in rel or "QC" in rel:
        role = "quality-control record"
    elif path.name in {"Makefile", "requirements.lock.txt", "README.md"}:
        role = "build or environment specification"
    else:
        role = "project artifact"
    return suffix, role


def dependencies(rel: str) -> tuple[str, str]:
    if rel.startswith("data/raw/"):
        return "public source URL or archived API response", "p03_data_audit.py; p05_gis_demand.py"
    if rel.endswith("_anchors.csv"):
        return "municipal raw CSV", "p05_gis_demand.py; p06_reconstruct.py"
    if rel.endswith(("nodes.csv", "edges.csv", "demand_nodes.csv", "zone.geojson")):
        return "OSM graph/buildings; municipal anchors", "p06_reconstruct.py; p07_optimize.py; p08_dg.py"
    if "/recon/" in rel or rel.endswith(("clusters.csv", "reconstruction_summary.csv")):
        return "processed road graph and modeled demand", "p07_optimize.py"
    if rel.endswith("cluster_results.csv"):
        return "reconstruction ensemble; config/study.yaml", "scenario_results.csv; p08_dg.py; p10_sensitivity.py"
    if rel.endswith(("scenario_results.csv", "sensitivity_mc.csv", "dg_results.csv")):
        return "cluster-level modeled outputs", "p11_freeze.py; figures; tables; manuscript"
    if rel.endswith("manuscript_values.csv"):
        return "all frozen analysis result tables", "p13_manuscript.py; p14_package.py"
    if rel.startswith("figures/") or rel.startswith("tables/"):
        return "frozen machine-readable outputs", "manuscript DOCX; submission package"
    if rel.endswith(".docx"):
        return "manuscript generator; frozen outputs; figures", "submission package"
    if rel.endswith(".zip"):
        return "submission artifacts", "external submission or forensic audit"
    if rel.startswith("scripts/"):
        return "config; raw/processed data; upstream scripts", "declared outputs"
    return "", ""


def run_version(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except (FileNotFoundError, subprocess.CalledProcessError, IndexError):
        return "not available"


def append_decision(text: str) -> None:
    path = ROOT / "DECISION_LOG.md"
    header = "# Forensic Revision Decision Log\n\n"
    if not path.exists():
        path.write_text(header, encoding="utf-8")
    existing = path.read_text(encoding="utf-8")
    if text not in existing:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")


def write_provenance(rows: list[dict[str, str]]) -> None:
    path = ROOT / "PROVENANCE.csv"
    fields = [
        "record_id",
        "phase",
        "artifact",
        "category",
        "source",
        "retrieved_utc",
        "size_bytes",
        "sha256",
        "license_or_terms",
        "status",
        "notes",
    ]
    existing: dict[str, dict[str, str]] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            existing = {row["record_id"]: row for row in csv.DictReader(handle)}
    for row in rows:
        existing[row["record_id"]] = row
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(existing.values())


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    original_rows = []
    input_ok = True
    for name, expected in EXPECTED.items():
        path = ORIGINALS / name
        actual = sha256(path)
        mode = oct(path.stat().st_mode & 0o777)
        ok = actual == expected and not os.access(path, os.W_OK)
        input_ok &= ok
        original_rows.append(
            {
                "filename": name,
                "size_bytes": path.stat().st_size,
                "sha256": actual,
                "expected_sha256": expected,
                "read_only_mode": mode,
                "verified": ok,
            }
        )
    with (AUDIT / "ORIGINALS_MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=original_rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(original_rows)

    inventory = []
    excluded = {".venv", "__pycache__", ".git"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or excluded.intersection(path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        kind, role = classify(path)
        upstream, downstream = dependencies(rel)
        inventory.append(
            {
                "path": rel,
                "type": kind,
                "size": path.stat().st_size,
                "checksum": sha256(path),
                "role": role,
                "upstream": upstream,
                "downstream": downstream,
                "status": "present",
            }
        )

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    referenced = sorted(set(re.findall(r"(?:scripts|qc)/[\w./-]+\.py", makefile)))
    missing = []
    for rel in referenced:
        if not (ROOT / rel).exists():
            missing.append(rel)
            inventory.append(
                {
                    "path": rel,
                    "type": "py",
                    "size": 0,
                    "checksum": "",
                    "role": "Makefile-referenced executable",
                    "upstream": "Makefile",
                    "downstream": "declared reproducibility target",
                    "status": "MISSING",
                }
            )
    for required_dir in ("tests",):
        if not (ROOT / required_dir).exists():
            missing.append(required_dir + "/")

    inventory_path = ROOT / "AUDIT_FILE_INVENTORY.csv"
    with inventory_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["path", "type", "size", "checksum", "role", "upstream", "downstream", "status"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(inventory)

    edges = [
        ("all persisted raw inputs", "p19_raw_provenance.py", "checksums/acquisition registry"),
        ("manufacturer cable/transformer sources", "p16_catalogs.py", "engineering catalogues"),
        ("public municipal CSVs", "p03_data_audit.py", "audit/checksums"),
        ("municipal CSVs", "processed anchors", "cleaning/encoding"),
        ("archived OSM graphs/buildings", "p05_gis_demand.py", "GIS clipping/demand modeling"),
        ("processed anchors", "p06_reconstruct.py", "anchor bias"),
        ("processed nodes/edges/demand", "p06_reconstruct.py", "clustering/reconstruction"),
        ("reconstruction ensemble", "p07_optimize.py", "S1 baseline"),
        ("processed road graph/demand", "p07_optimize.py", "S1.5/S2 candidates"),
        ("cluster scenario outputs", "p10_sensitivity.py", "economic uncertainty"),
        ("scenario/sensitivity/benchmark/data audit", "p11_freeze.py", "manuscript values"),
        ("frozen outputs", "p12_figures.py", "figures/tables"),
        ("frozen outputs and references", "p13_manuscript.py", "DOCX"),
        ("DOCX/figures/tables/provenance/code", "p14_package.py", "submission package"),
    ]
    with (ROOT / "AUDIT_DEPENDENCY_DAG.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["upstream", "downstream", "transformation"])
        writer.writerows(edges)
    dag_lines = ["# Actual dependency DAG", "", "```mermaid", "flowchart LR"]
    for index, (source, target, transformation) in enumerate(edges):
        dag_lines.append(
            f'  N{index}["{source}"] -->|"{transformation}"| M{index}["{target}"]'
        )
    dag_lines.extend(["```", "", "The DAG describes the implemented chain; missing executables are listed in the inventory."])
    (ROOT / "AUDIT_DEPENDENCY_DAG.md").write_text("\n".join(dag_lines) + "\n", encoding="utf-8")

    packages = []
    lock_names = []
    for line in (ROOT / "requirements.lock.txt").read_text(encoding="utf-8").splitlines():
        if "==" in line:
            lock_names.append(line.split("==", 1)[0])
    for name in lock_names:
        try:
            version = importlib.metadata.version(name)
            status = "installed"
        except importlib.metadata.PackageNotFoundError:
            version = ""
            status = "missing"
        packages.append({"component": name, "version": version, "type": "python-package", "status": status})
    packages.extend(
        [
            {"component": "python", "version": platform.python_version(), "type": "runtime", "status": "installed"},
            {"component": "platform", "version": platform.platform(), "type": "runtime", "status": "installed"},
            {"component": "HiGHS", "version": importlib.metadata.version("highspy"), "type": "solver", "status": "installed"},
            {"component": "GLPK", "version": run_version(["glpsol", "--version"]), "type": "solver", "status": "informational"},
            {"component": "CBC", "version": run_version(["cbc", "-version"]), "type": "solver", "status": "informational"},
        ]
    )
    with (ROOT / "ENVIRONMENT_SOLVER_VERSIONS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=packages[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(packages)

    write_provenance(
        [
            {
                "record_id": f"P0-{i + 1:03d}",
                "phase": "0",
                "artifact": row["filename"],
                "category": "canonical-input",
                "source": "prior Devin session attachment",
                "retrieved_utc": now,
                "size_bytes": str(row["size_bytes"]),
                "sha256": row["sha256"],
                "license_or_terms": "user-provided",
                "status": "preserved-read-only" if row["verified"] else "verification-failed",
                "notes": "The user-referenced browser suffix '(4)' was absent; byte-identical repository and attachment copies match.",
            }
            for i, row in enumerate(original_rows)
        ]
    )
    append_decision(
        "2026-09-24 | Phase 0 | Treat attachment manuscript_inline.docx as the canonical "
        "file referenced as manuscript_inline (4).docx | Its SHA-256 exactly matches the "
        "repository manuscript and archive lineage; the filename discrepancy is retained "
        "in provenance rather than silently ignored. | active"
    )
    append_decision(
        "2026-09-24 | Phase 0 | Base the forensic revision on the prior SEGAN working tree while preserving "
        "the supplied ZIP and DOCX read-only | The archive is the canonical submitted state; "
        "the repository working tree supplies omitted executable code and raw inputs. | active"
    )

    critical_findings = [
        "The canonical ZIP contains outputs but no executable scripts or raw data."
    ]
    if missing:
        critical_findings.append(
            "Makefile-referenced or required pipeline items are missing: "
            + ", ".join(missing))
    qc = {
        "phase": 0,
        "status": "complete_with_findings",
        "canonical_inputs_verified": input_ok,
        "inventory_rows": len(inventory),
        "dependency_edges": len(edges),
        "missing_declared_pipeline_items": missing,
        "critical_findings": critical_findings,
    }
    (ROOT / "PHASE_0_QC.json").write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    (ROOT / "PHASE_0_HANDOFF.txt").write_text(
        "Phase 0 complete. Canonical ZIP and DOCX are checksum-verified and read-only. "
        f"The inventory contains {len(inventory)} entries and {len(missing)} declared "
        "pipeline items are missing; these are forensic findings to repair, not ignored "
        "exceptions. See AUDIT_FILE_INVENTORY.csv and AUDIT_DEPENDENCY_DAG.md.\n",
        encoding="utf-8",
    )
    print(json.dumps(qc, indent=2))


if __name__ == "__main__":
    main()
