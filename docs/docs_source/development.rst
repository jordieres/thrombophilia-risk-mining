Development and verification
================================

Documentation contracts
---------------------------

New scientific code and user-facing documentation are written in English.
Maintain the implementation details in :doc:`manuscript_reanalysis` whenever
cohort definitions, predictors, tuning, threshold selection or export schemas
change. ``src/manuscript_reporting.py`` is the source of generated coauthor
replies and manuscript replacement text; editing a generated report alone is
not a durable correction.

The authoritative analysis is distinct from the historical exploratory CLI.
Do not use generic ``score`` output to update paper metrics. Historical aggregate files are preserved under ``out/archive/``. The 7 September
explicit-results alternative is labelled separately in ``out/README.md``.
The previous unsafe model loop in ``manuscript_support.py`` has been removed;
its public command delegates to the new analysis.

Tests
---------

Run the repository suite:

.. code-block:: bash

   python -m pytest tests -q

The focused scientific regression suite is:

.. code-block:: bash

   python -m pytest tests/test_manuscript_reanalysis.py -q

It protects tested-only subtype controls, known-carrier exclusions, unknown
versus negative categories, fixed numeric boundaries, forbidden predictors,
dense tree-missing semantics, calibration of actual integer points,
training-only thresholds, unique held-out predictions and confusion-matrix
resource identities. Production output checks additionally verify disjoint
temporal eras and paired primary patient populations.

Use a test-only compact integration run in a fresh temporary directory before
starting expensive reanalyses. Do not overwrite a completed run to test a new
implementation. Changes to numerical source files alter the resume signature;
use a fresh result directory when scientific code changes.

Documentation build
-----------------------

Install the Poetry ``docs`` dependency group or equivalent Sphinx dependencies.
The executable HTML build is:

.. code-block:: bash

   python -m sphinx -W --keep-going -b html docs/docs_source docs

``-W`` makes warnings actionable. The build uses docstrings from the actual
modules, not hand-copied API declarations. ``docs/docs_source`` is the editable
Sphinx source; ``docs`` is the published HTML root. Do not accidentally write a
second generated tree under ``docs/docs``. Existing duplicate historical pages
should link readers to the canonical documentation.

The build uses optional external intersphinx inventories. For an explicitly
offline build, provide a small configuration override disabling
``intersphinx_mapping``; do not claim that a network inventory failure is a code
or scientific-validation failure.

Type hints and dependency management
----------------------------------------

The modules use annotations and documented input/output contracts. The project
does not currently declare a mypy quality gate; do not claim a strict mypy check
has passed without installing/configuring and running one. Runtime and data
integrity tests are the current executable quality gates.

``pyproject.toml`` and ``requirements.txt`` describe supported dependency ranges.
``requirements-manuscript.txt`` records the exact tested analysis/reporting
versions for a Python 3.12 environment. ``run_manifest.json`` independently records
the packages used in each numerical execution. A dependency lock describes an
installation resolution, not proof that those versions generated old results.

Repository layout
---------------------

``src/manuscript_*.py``
   Cohort contracts, estimators, orchestration, reporting and compatibility APIs.

``src/exp_*.py`` and ``src/cli.py``
   Historical exploratory framework; preserved for existing experiments.

``tests/``
   Regression and integration-oriented tests.

``docs/docs_source/``
   English Sphinx source, including the complete manuscript manual.

``out/manuscript_reanalysis_2026-09-08/``
   Completed numerical evidence, generated English replies/text and figures.

``out/archive/manuscript_audit_2026-09-07/``
   Initial audit of the supplied documents and historical outputs.

``data/``
   Local source snapshots and the supplied variable dictionary. Do not infer
   cohort eligibility from a prepared file whose original labels were removed.

Publication artifact checks
---------------------------

After staging the intended changes, run:

.. code-block:: bash

   python scripts/check_repository_artifacts.py

The check rejects patient-level predictions, individual CSVs, model binaries,
optional Word/PDF files, Sphinx caches and executed notebook outputs in the Git
index. It also verifies every public manifest reference is tracked and matches
its checksum. Local-only and optional artifact absence is valid in a clone.
The script does not inspect or rewrite historical commits.
