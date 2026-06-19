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

Contrast mining on large datasets
---------------------------------

The contrast workflow now includes explicit memory guards, bounded rule search,
and resumable checkpoints. On large datasets, prefer configuring the contrast
run with a modest sample budget, a strict support threshold, and a checkpoint
folder that can be reused with ``--resume`` after an interrupted run.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment contrast \
     --contrast-max-samples 300 \
     --contrast-min-support 0.05 \
     --contrast-min-confidence 0.40 \
     --contrast-max-feature-cardinality 12 \
     --contrast-max-features 48 \
     --contrast-max-rule-size 3 \
     --contrast-top-k-per-outcome 5 \
     --contrast-workers 2 \
     --checkpoint-dir out/checkpoints \
     --output-dir out \
     --resume

The contrast checkpoint directory stores four stages:

``01_prepared_sample.parquet``
   Stratified sample plus the selected low-cardinality columns.

``02_encoded_transactions.parquet``
   Sparse one-hot transactional matrix serialized as compact integer values.

``03_frequent_itemsets.parquet``
   Frequent itemsets mined with the configured support and maximum rule length.

``04_target_rules.parquet``
   Final outcome-targeted rules ready for LaTeX and Plotly export.

Multi-line shell commands
-------------------------

When writing a Bash command across multiple lines, every continued line must be
escaped with ``\``. Without that escape character, Bash treats the next line as
an entirely new command.

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
     --contrast-min-support 0.05 \
     --contrast-min-confidence 0.40 \
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
   Controls sampling, support/confidence thresholds, low-cardinality feature
   selection, maximum rule size, worker count, and checkpoint reuse.

``clustering``
   Controls the number of sampled rows, requested clusters, and maximum t-SNE
   perplexity.

Artifact locations
------------------

Use ``--output-dir`` to redirect interactive HTML charts away from the project
root, and ``--checkpoint-dir`` to persist resumable intermediate state for
long-running experiments.

VS Code debugging
-----------------

A preconfigured ``.vscode/launch.json`` file is included so the CLI can be
launched under ``debugpy`` with promptable dataset and sampling parameters.
