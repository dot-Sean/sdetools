import sys

try:
    import py2exe
except ImportError:
    print "Error: Missing py2exe package. Use this for windows compilation only."
    sys.exit(1)

from distutils.core import setup

import modules
options = {
    'py2exe': {
        'includes':[]
    }
}

for mod_name in modules.__all__:
    options['py2exe']['includes'].append('modules.%s' % mod_name)

setup(
    console=['sde.py'],
    zipfile=None,
    options=options
    )
