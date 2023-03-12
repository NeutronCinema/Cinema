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
    'breathe',
    'exhale',
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

import os
import sys
import textwrap
from matplotlib.pyplot import text
print(sys.executable)
import pyvista

os.environ["CDOCROOT"] = os.path.dirname(__file__)
os.environ["CDOCGDML"] = os.path.join(os.getenv("CDOCROOT"),'prompt' ,'usersmanual', 'geometry')
os.environ["CDOCUTILS"] = os.path.join(os.getenv("CDOCROOT"), 'utils')
os.environ['PYTHONPATH'] = ':'.join((os.getenv("CDOCUTILS"), os.environ.get('PYTHONPATH', '')))
sys.path.insert(0, os.path.abspath('..'))

# To start framebuffer: required if built in VM or docker (where is the case of readthedocs)
# pyvista.start_xvfb()

# Setup the breathe extension
breathe_projects = {
    "cinema": "./_doxygen/xml"
}
breathe_default_project = "cinema"

# Setup the exhale extension
exhale_args = {
    # These arguments are required
    "containmentFolder":     "./api",
    "rootFileName":          "library_root.rst",
    "doxygenStripFromPath":  "..",
    # Heavily encouraged optional argument (see docs)
    "rootFileTitle":         "Library API",
    # Suggested optional arguments
    "createTreeView":        True,
    # TIP: if using the sphinx-bootstrap-theme, you need
    # "treeViewIsBootstrap": True,
    "exhaleExecutesDoxygen": True,
    "exhaleDoxygenStdin":    textwrap.dedent('''
        INPUT = ../../src/cxx
        EXTRACT_ALL = YES
        CLASS_DIAGRAMS = YES
        HIDE_UNDOC_RELATIONS = NO
        HAVE_DOT = YES
        CLASS_GRAPH = YES
        COLLABORATION_GRAPH = YES
        UML_LOOK = YES
        UML_LIMIT_NUM_FIELDS = 50
        TEMPLATE_RELATIONS = YES
        DOT_GRAPH_MAX_NODES = 100
        MAX_DOT_GRAPH_DEPTH = 0
        DOT_TRANSPARENT = YES
        GENERATE_LATEX = YES
        ''')
        
}

# Tell sphinx what the primary language being documented is.
primary_domain = 'cpp'

# Tell sphinx what the pygments highlight language should be.
highlight_language = 'cpp'


package_path = os.path.abspath('../..')
os.environ['PYTHONPATH'] = ':'.join((package_path, os.environ.get('PYTHONPATH', '')))

imgmath_image_format = 'svg'
imgmath_font_size = 14
imgmath_use_preview = True

# if png format is required
# imgmath_dvipng_args = ['-gamma', '1.5', '-D', '110', '-bg', 'Transparent']

# intersphinx_mapping = {
#     'python': ('https://docs.python.org/3/', None),
#     'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
# }
# intersphinx_disabled_domains = ['std']

# templates_path = ['_templates']

# -- Options for HTML output
html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
# epub_show_urls = 'footnote'

# -- LaTex output configuration -----------------
# it seems like a hard job to simply add a custom document class (.cls)
# the solution here is to bind sphinx and latex step by step
# https://github.com/sphinx-doc/sphinx/pull/6969#pullrequestreview-369699459
latex_additional_files = [
    './theme/elsarticle.cls',
    './theme/sphinx.sty',
    './theme/sphinxlatexstyletext.sty',
    './theme/sphinxlatexstyleheadings.sty',
    './theme/sphinxlatexstylepage.sty',
    './theme/sphinxlatexliterals.sty',
    './theme/sphinxmessages.sty',
]

latex_theme_path = [
    './theme/elsarticle.cls'
]

latex_toplevel_sectioning = 'section'

# latex_theme = ''

latex_documents = [
    ('prompt/paper', 'cinema.tex', 
    'Prompt: Probability-Conserved Cross Section Biasing Monte Carlo Particle Transport System', '', 
    'elsarticle', True)
]

latex_appendices = ['./prompt/usersmanual/geometry']

latex_table_style = ['booktabs', 'nocolorrows']

latex_elements = {
    'papersize': r'preprint',
    'tableofcontents': r'',
    # 'pointsize': r'10pt',
    # refer to CPC_template.tex for options available
    'extraclassoptions': r'times',
    'fontpkg': r"""
% \usepackage{txfonts}
% \renewcommand{\familydefault}{\rmdefault}
""",
    'fncychap': '',
    'preamble': r"""
\usepackage{booktabs}
% affect only figure and table, as known
\usepackage[font=small,labelfont=bf]{caption}
    """
}

latex_logo = os.path.join('img', 'logo.png')


