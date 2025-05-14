# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'parreg'
copyright = '2025, Yuqiong Liu'
author = 'Yuqiong Liu'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon"
]

templates_path = ['_templates']
exclude_patterns = []

autodoc_member_order = 'bysource'

autodoc_default_options = {
    "members": True,
    "private-members": True,  
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'alabaster'
html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']

import os
import sys
sys.path.insert(0, os.path.abspath('../../src/parreg/'))  # Adjust the path to your source code


def skip_pydantic_model_config(app, what, name, obj, skip, options):
    if name in {"model_config", "model_fields", "model_post_init", "_abc_impl"}:
        return True  
    return skip

def setup(app):
    app.connect("autodoc-skip-member", skip_pydantic_model_config)