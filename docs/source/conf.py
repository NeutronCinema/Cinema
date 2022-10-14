# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'Cinema'
copyright = '2022, CSNS'
author = 'Xiao Xiao Cai'

release = '0.0.1'
version = '0.0.1'

# -- General configuration

extensions = [
    # 'nbsphinx',
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'jupyter_sphinx',
    "pyvista.ext.plot_directive",
    "pyvista.ext.coverage",
    'sphinx.ext.imgmath',
]

import os, sys
import pyvista

os.environ["CDOCROOT"] = os.path.dirname(__file__)
os.environ["CDOCGDML"] = os.path.join(os.getenv("CDOCROOT"), 'usersmanual', 'geometry')
os.environ["CDOCUTILS"] = os.path.join(os.getenv("CDOCROOT"), '_utils')
os.environ['PYTHONPATH'] = ':'.join((os.getenv("CDOCUTILS"), os.environ.get('PYTHONPATH', '')))

# To start framebuffer: required if built in VM or docker (where is the case of readthedocs)
pyvista.start_xvfb()

# package_path = os.path.abspath('../..')
# os.environ['PYTHONPATH'] = ':'.join((package_path, os.environ.get('PYTHONPATH', '')))

# imgmath_image_format = 'svg'
imgmath_font_size = 14
imgmath_use_preview = True

# if png format is required
# imgmath_dvipng_args = ['-gamma', '1.5', '-D', '110', '-bg', 'Transparent']

intersphinx_mapping = {
#     'python': ('https://docs.python.org/3/', None),
#     'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
# }
# intersphinx_disabled_domains = ['std']

# templates_path = ['_templates']

# -- Options for HTML output
html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
# epub_show_urls = 'footnote'
