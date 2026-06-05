Usage
=====

CLI entry point
---------------

The project exposes a single CLI entry point implemented in ``src/cli.py``.

.. code-block:: bash

   poetry run python src/cli.py --data data/patD.parquet --experiment all

Configurable experiment budgets
-------------------------------

The CLI exposes knobs for experiments that may otherwise be expensive on large
clinical datasets.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment permutation \
     --permutation-max-samples 800 \
     --permutation-max-splits 2 \
     --permutation-repeats 1 \
     --permutation-estimators 10

Multi-line shell commands
-------------------------

When writing a Bash command across multiple lines, every continued line must be
escaped with ``\``. Without that escape character, Bash treats the next line as
a brand-new command.

Correct multi-line example
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment all \
     --permutation-max-samples 2000 \
     --permutation-max-splits 2 \
     --permutation-repeats 1 \
     --permutation-estimators 10 \
     --contrast-max-samples 300 \
     --clustering-max-samples 1000

Incorrect multi-line example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   poetry run python src/cli.py --data data/patD.parquet --experiment all
   --permutation-max-samples 2000
   --permutation-max-splits 2

In the incorrect example, the first line runs the CLI and the following lines
are interpreted by the shell as independent commands, which leads to
``command not found`` messages.

Available configuration groups
------------------------------

``permutation``
   Controls sampling, fold count, permutation repeats, and XGBoost tree count.

``contrast``
   Controls sampling, support threshold, selected categorical features, and
   accepted feature cardinality.

``clustering``
   Controls the number of sampled rows, requested clusters, and maximum t-SNE
   perplexity.

VS Code debugging
-----------------

A preconfigured ``.vscode/launch.json`` file is included so the CLI can be
launched under ``debugpy`` with promptable dataset and sampling parameters.
