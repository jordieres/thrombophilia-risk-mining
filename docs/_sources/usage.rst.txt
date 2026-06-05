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

   poetry run python src/cli.py      --data data/patD.parquet      --experiment permutation      --permutation-max-samples 800      --permutation-max-splits 2      --permutation-repeats 1      --permutation-estimators 10

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
