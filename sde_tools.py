#!/usr/bin/python
import sys, os

from sdelib.conf_mgr import config

if sys.platform.startswith("win"):
    current_file = sys.argv[0]
else:
    current_file = __file__
sys.path.append(os.path.split(os.path.abspath(current_file))[0])

def main(argv):
    pass

if __name__ == "__main__":
    main(sys.argv)

