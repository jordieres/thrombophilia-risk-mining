Installation
============

The project uses `Poetry <https://python-poetry.org/>`_ for dependency
management.

Runtime installation
--------------------

.. code-block:: bash

   poetry install

Documentation dependencies
--------------------------

Sphinx dependencies are declared in the ``docs`` dependency group.
The regular installation command above is sufficient for local development.

Type-checking dependencies
--------------------------

Static typing support is declared in the ``dev`` dependency group and includes:

* ``mypy`` for formal static analysis.
* ``pandas-stubs`` for richer pandas typing support.
