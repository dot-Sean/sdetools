import os
import sys

if sys.version < '2.4':
    print 'This package needs python 2.4+'
    sys.exit(1)

from distutils.core import setup

import sdetools
from sdetools.sdelib import commons

ext_opt = {
    'options': {}
    }

def set_py2exe_options():
    from sdetools import modules
    ext_opt['options']['py2exe'] = {
            'includes':[]
        }

    for mod_name in modules.__all__:
        ext_opt['options']['py2exe']['includes'].append('sdetools.modules.%s' % mod_name)
    
    ext_opt['console'] = ['sde.py']
    ext_opt['zipfile'] = None

try:
    import py2exe # noqa
except ImportError:
    if 'py2exe' in sys.argv[1:]:
        print "Error: Missing py2exe package."
        sys.exit(1)
else:
    set_py2exe_options()

if 'py2exe' not in sys.argv[1:]:
    import setuptools
    ext_opt['packages'] = setuptools.find_packages()
    ext_opt['package_data'] = {'sdetools':['docs/*/*']}

static_files = []
root_path = os.path.split(commons.base_path)[0]
for root, dirnames, filenames in os.walk(commons.media_path):
    if not filenames:
        continue
    static_files.append((root[len(root_path)+1:], [os.path.join(root, fn) for fn in filenames]))

f = open(os.path.join(os.path.dirname(__file__), 'README.md'))
readme = f.read()
f.close()

setup(
    name='sdetools',
    description='SD Element Tools: A collection of SD Elements integration tools built around SD Elements API.',
    long_description=readme,
    maintainer="SD Elements",
    maintainer_email="support@sdelements.com",
    version=sdetools.VERSION,
    url='https://github.com/sdelements/sdetools',
    data_files=static_files,
    **ext_opt
    )
