#!/usr/bin/python
import sys
import os
import getopt

if sys.platform.startswith("win"):
    current_file = sys.argv[0]
else:
    current_file = __file__
BASE_PATH = os.path.split(os.path.abspath(current_file))[0]

MODULES_PATH = os.path.join(BASE_PATH, 'modules')
sys.path.append(BASE_PATH)

from sdelib import commons
commons.base_path = BASE_PATH

from sdelib import conf_mgr

def load_modules():
    command = {}

    for mod_name in os.listdir(MODULES_PATH):
        if mod_name.startswith('_'):
            continue
        try:
            mod = __import__('modules.' + mod_name)
        except ImportError:
            raise commons.UsageError('Unable to import module %s' % (mod_name))
        mod = getattr(mod, mod_name)
        if not hasattr(mod, 'Command'):
            raise commons.UsageError('Module missing Command class: %s' % (mod_name))
        cmd_cls = mod.Command
        cmd_name = mod_name[4:]
        if hasattr(cmd_cls, 'name'):
            cmd_name = cmd_cls.name
        if not hasattr(cmd_cls, 'help'):
            raise commons.UsageError('Missing help string for module %s' % (cmd_name))
        command[cmd_name] = cmd_cls
        command[cmd_name].cmd_name = cmd_name

    return command

def main(argv):
    command = load_modules()

    if len(argv) < 2:
        commons.show_error("Missing command", usage_hint=True)
        return False
    
    curr_cmd_name = None
    for arg in argv[1:]:
        if not arg.startswith('-'):
            curr_cmd_name = arg
            break

    if not curr_cmd_name:
        commons.show_error("Missing command", usage_hint=True)
        return False

    if curr_cmd_name not in command:
        commons.show_error("Command not found: %s" % (curr_cmd_name), usage_hint=True)
        return False

    curr_cmd = command[curr_cmd_name]

    config = conf_mgr.Config(command)
    ret = config.parse_args(argv)
    if not ret:
        return False

    cmd_inst = curr_cmd(config)
    cmd_inst.customize_config()
    try:
        ret_status = cmd_inst.handle(*argv[2:])
    except commons.Error, e:
        commons.show_error(str(e))
        return False

    if ret_status is None:
        ret_status = True
    return ret_status

if __name__ == "__main__":
    exit_stat = main(sys.argv)
    if not exit_stat:
        sys.exit(1)
    else:
        sys.exit(0)
