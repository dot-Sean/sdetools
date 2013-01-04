import logging

import conf_mgr
import commons

import modules

def load_modules():
    command = {}

    for mod_name in modules.__all__:
        if mod_name.startswith('_'):
            continue
        try:
            mod = __import__('modules.' + mod_name)
        except ImportError:
            logging.exception('Exception in importing module %s' % (mod_name))
            raise commons.UsageError('Unable to import module %s' % (mod_name))
        mod = getattr(mod, mod_name)
        if not hasattr(mod, 'Command'):
            raise commons.UsageError('Module missing Command class: %s' % (mod_name))
        cmd_cls = mod.Command
        if not hasattr(cmd_cls, 'name'):
            cmd_cls.name = mod_name
        if not hasattr(cmd_cls, 'help'):
            raise commons.UsageError('Missing help string for module %s' % (cmd_cls.name))
        command[cmd_cls.name] = cmd_cls

    return command

def run_command(cmd_name, args):
    command = load_modules()

    if cmd_name not in command:
        raise commons.UsageError("Command not found: %s" % (cmd_name))

    curr_cmd = command[cmd_name]

    config = conf_mgr.Config(command, args)

    cmd_inst = curr_cmd(config, args)

    cmd_inst.configure()

    ret_status = cmd_inst.parse_args()

    if not ret_status:
        return False

    cmd_inst.args = config.args
    cmd_inst.process_args()

    ret_status = cmd_inst.handle()

    if ret_status is None:
        ret_status = True
    return ret_status

