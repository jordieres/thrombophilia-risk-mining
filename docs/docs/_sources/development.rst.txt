Development
===========

Documentation conventions
-------------------------

The source code is documented with English Google-style docstrings so Sphinx can
extract API documentation through ``autodoc`` and ``napoleon``.

Type checking
-------------

Type checking is formalized in ``pyproject.toml`` through the ``[tool.mypy]``
section. The project currently enforces:

* explicit type annotations on functions and methods,
* validation of untyped function bodies,
* no implicit optional parameters,
* warnings for redundant casts and unused ignores,
* strict equality checks.

Run the checker with:

.. code-block:: bash

   poetry run mypy src

Build the documentation
-----------------------

Generate the HTML documentation locally with:

.. code-block:: bash

   poetry run sphinx-build -d docs_source/.doctrees -b html docs_source docs

Project structure
-----------------

``src/``
   Application source code, preprocessing utilities, and experiment modules.

``docs_source/``
   Editable Sphinx configuration and reStructuredText source files.

``docs/``
   Published HTML documentation generated from ``docs_source/``.

``.vscode/launch.json``
   Debugger configuration for interactive CLI runs.
