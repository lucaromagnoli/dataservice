import os
import sys

from dataservice import DataService, HttpXClient, Pipeline, Request, Response

sys.path.insert(0, os.path.abspath("../dataservice"))

project = "DataService"
copyright = "2024, Luca Romagnoli"
author = "Luca Romagnoli"
release = "0.0.1"

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.autodoc_pydantic",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

autodoc_pydantic_model_show_json = True
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_config_section = False
