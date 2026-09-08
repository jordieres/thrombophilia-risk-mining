"""Check the Git index for local-only research artifacts and stale public manifests.

Run from any working directory with ``python scripts/check_repository_artifacts.py``.
This reads filenames, notebook output presence, CSV headers and file hashes; it
never prints patient values. It checks the next commit's tracked-file selection,
using working-tree contents for staged paths. It does not inspect or rewrite Git
history. Run after staging intended changes and before publishing a commit.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from manuscript_artifacts import verify_public_artifacts


def check_repository(root: Path = ROOT) -> list[str]:
    """Return actionable paths, without patient data, for forbidden tracked content."""
    names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    names=[n for n in names if n];tracked=set(names);errors=[]
    for name in names:
        path=root/name
        if not path.is_file():
            errors.append(f'Tracked path missing from working tree: {name}')
            continue
        if '.doctrees/' in name:
            errors.append(f'Generated cache is tracked: {name}')
        if name.startswith('out/'):
            if path.suffix.lower() in {'.parquet','.joblib','.pickle','.docx','.pdf','.log'}:
                errors.append(f'Local-only research/export artifact is tracked: {name}')
            if path.suffix.lower()=='.csv':
                with path.open(encoding='utf-8') as handle:header=next(csv.reader(handle),[])
                if {'id_pacie','patient_id'} & set(header):
                    errors.append(f'Patient-level CSV is tracked: {name}')
            if path.suffix.lower()=='.html':
                errors.append(f'Legacy interactive output requires local storage: {name}')
        if path.suffix=='.ipynb':
            notebook=json.loads(path.read_text())
            if any(cell.get('outputs') for cell in notebook.get('cells',[])):
                errors.append(f'Executed notebook outputs are tracked: {name}')
        if name.endswith('/run_manifest.json') and name.startswith('out/manuscript_reanalysis_'):
            manifest=json.loads(path.read_text())
            if manifest.get('status')!='complete':errors.append(f'Incomplete published run: {name}')
            if manifest.get('artifact_schema_version')!=2:errors.append(f'Unsplit artifact manifest: {name}')
            errors.extend(verify_public_artifacts(path.parent,manifest))
            for relative in manifest.get('outputs_sha256',{}):
                candidate=str((path.parent/relative).relative_to(root))
                if candidate not in tracked:errors.append(f'Public artifact not in Git index: {candidate}')
    return errors


if __name__=='__main__':
    errors=check_repository()
    if errors:
        print('\n'.join(errors));raise SystemExit(1)
    print('Repository artifact checks passed: aggregate evidence only; public manifests resolve.')
