Installation
============

Manuscript analysis environment
-------------------------------

Use Python 3.12 and the exact tested stack for reproducing the current numerical
run and document exports:

.. code-block:: bash

   python3.12 -m venv .venv-manuscript
   .venv-manuscript/bin/python -m pip install -r requirements-manuscript.txt

The pinned file includes NumPy, pandas, SciPy, scikit-learn, XGBoost, PyArrow,
openpyxl, mlxtend, joblib and matplotlib. Pandoc is an optional system executable
for DOCX generation. The Markdown and CSV outputs do not require Pandoc.
See :doc:`manuscript_reanalysis` for raw input requirements and the full command.

Broader exploratory toolkit
----------------------------

The project also uses Poetry for its broader dependency specification:

.. code-block:: bash

   poetry install

``requirements.txt`` is a range-based alternative covering the runtime toolkit.
Do not confuse the range-based install with the exact versions recorded in a
completed analysis manifest. The historical notebooks may contain earlier
assumptions and are not the authoritative manuscript command.

Development and documentation
-----------------------------

The Poetry ``dev`` group includes pytest. The ``docs`` group includes Sphinx
and Furo. Alternatively install these packages in the existing environment:

.. code-block:: bash

   python -m pip install pytest sphinx furo

Then follow :doc:`development` for tests and the warning-as-error documentation
build. No configured mypy gate is claimed by this repository.
