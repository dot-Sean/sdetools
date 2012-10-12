#!/usr/bin/python
import sys
import os
import getopt

if sys.platform.startswith("win"):
    current_file = sys.argv[0]
else:
    current_file = __file__
base_path = os.path.split(os.path.abspath(current_file))[0]
sys.path.append(base_path)

from sdelib import commons
commons.base_path = base_path

from sdelib import conf_mgr

def load_modules():
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

    return command

def main(argv):
    if len(argv) < 2:
        commons.show_error("Missing command", usage_hint=True)
        return 1
    
    curr_cmd_name = None
    for arg in argv[1:]:
        if not arg.startswith('-'):
            curr_cmd_name = arg
            break
    if not curr_cmd_name:
        commons.show_error("Missing command", usage_hint=True)
        return 1

    command = load_modules()
    if curr_cmd_name not in command:
        commons.show_error("Command not found: %s" % (curr_cmd_name), usage_hint=True)
        return 1

    curr_cmd = command[curr_cmd_name]

    config = conf_mgr.Config()
    ret = config.parse_args(argv)
    if not ret:
        return 1

    cmd_inst = curr_cmd(config)
    cmd_inst.customize_config()
    cmd_inst.handle(*argv[2:])

    return 0

if __name__ == "__main__":
    ret = main(sys.argv)
    
