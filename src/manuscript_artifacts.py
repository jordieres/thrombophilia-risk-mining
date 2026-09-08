"""Separate distributable evidence from local research data and optional exports.

Public manifests verify aggregate tables, narrative sources and figures without
requiring patient predictions, fitted models or Word exports in a Git checkout.
Local artifact hashes remain available for a complete research-environment audit.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    """Return a content hash for provenance, independently of Git tracking."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_kind(path: Path) -> str:
    """Classify derived files without publishing patient-level data by default."""
    if path.suffix.lower() in {'.docx', '.pdf'}:
        return 'optional_exports'
    if path.suffix.lower() in {'.parquet', '.joblib', '.pickle', '.doctree', '.log'}:
        return 'local_artifacts'
    if path.suffix.lower() == '.csv':
        # Defensive guard: an accidentally exported row-level CSV stays local.
        header = path.open(encoding='utf-8').readline().strip().split(',')
        if any(c.strip('"') in {'id_pacie', 'patient_id'} for c in header):
            return 'local_artifacts'
    return 'outputs_sha256'


def artifact_inventory(output: Path) -> dict:
    """Build a version-2 inventory with separate public, local and optional hashes."""
    result = {'artifact_schema_version': 2, 'outputs_sha256': {},
              'local_artifacts': {}, 'optional_exports': {}}
    for path in sorted(output.rglob('*')):
        if not path.is_file() or path.name == 'run_manifest.json':
            continue
        result[artifact_kind(path)][str(path.relative_to(output))] = sha256(path)
    return result


def verify_public_artifacts(output: Path, manifest: dict) -> list[str]:
    """Return public missing/hash errors; absence of local/optional files is valid."""
    errors = []
    for name, digest in manifest.get('outputs_sha256', {}).items():
        path = output / name
        if not path.is_file():
            errors.append(f'Missing public artifact: {name}')
        elif sha256(path) != digest:
            errors.append(f'Public artifact hash mismatch: {name}')
    return errors
