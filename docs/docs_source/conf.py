"""Sphinx configuration for the thrombophilia risk mining project."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
SOURCE_DIR = ROOT / "src"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE_DIR))

project = "Thrombophilia Risk Mining"
author = "Lucia Ordieres-Ortega"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.graphviz",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"
autodoc_mock_imports = ["pgmpy"]
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

graphviz_output_format = "svg"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["Thumbs.db", ".DS_Store"]
html_theme = "furo" if importlib.util.find_spec("furo") is not None else "alabaster"

# GitHub Pages needs this file in the published ``docs/`` root, but the file is
# already tracked directly in that output directory so Sphinx does not need to
# copy it through ``html_extra_path``.
