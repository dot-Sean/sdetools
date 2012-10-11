import sys

try:
    import py2exe
except ImportError:
    print "Error: Missing py2exe package. Use this for windows compilation only."
    sys.exit(1)

from distutils.core import setup

setup(console=['sde_tools.py'])
