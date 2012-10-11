#!/usr/bin/python
import sys, os

if sys.platform.startswith("win"):
    current_file = sys.argv[0]
else:
    current_file = __file__
base_path = os.path.split(os.path.abspath(current_file))[0]
sys.path.append(base_path)

from sdelib import commons
commons.base_path = base_path

def main(argv):
    pass

if __name__ == "__main__":
    main(sys.argv)

