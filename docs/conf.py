# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

#from ja2mqtt import __version__

import os
import re
import sys

#from directives import GDriveDrawing

project = 'ja2mqtt'
copyright = '2023, Tomas Vitvar'
author = 'Tomas Vitvar'
release = '1.0'

# determine the version of ja2mqtt
try:
    version_file = os.path.join(os.path.realpath(os.path.dirname(__file__) + "/.."),'ja2mqtt', '__init__.py')
    __version__ = re.search('__version__\s+=\s+\"([0-9\.a-z]+)\"', open(version_file).read()).group(1)
    print(f"ja2mqtt version is {__version__}")
except Exception as e:
    raise Exception(f"Cannot determine the ja2mqtt version from {version_file}. {str(e)}")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

sys.path.append(os.path.abspath('_exts'))

extensions = ['myst_parser',  'sphinx.ext.autosectionlabel',  'sphinx_copybutton', 'gdrawing']

copybutton_only_copy_prompt_lines = True
copybutton_prompt_text = "$ "

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

myst_heading_anchors = 2
autosectionlabel_prefix_document = True

highlight_language = 'jinja'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_title = f"ja2mqtt v{__version__}"
language = "en"

html_static_path = ["_static"]
html_css_files = ["pied-piper-admonition.css", "css/custom.css"]

html_theme_options: Dict[str, Any] = {
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/tomvit/ja2mqtt",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
    "source_repository": "https://github.com/tomvit/ja2mqtt/",
    "source_branch": "master",
    "source_directory": "docs/",
}
