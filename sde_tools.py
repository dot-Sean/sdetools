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
    command = {}

    for mod_name in os.listdir(base_path):
        if not mod_name.startswith('mod_'):
            continue
        if not os.path.isdir(mod_name):
            continue
        mod = __import__(mod_name)
        cmd_name = mod_name[4:]
        command[cmd_name] = mod.Command
        command[cmd_name].cmd_name = cmd_name

if __name__ == "__main__":
    main(sys.argv)

