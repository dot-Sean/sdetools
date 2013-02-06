import logging
logger = logging.getLogger(__name__)

import conf_mgr
import commons

from sdetools import modules

def stdout_callback(obj):
    print obj

class Info(object):
    def __init__(self, title='', itype='info', **items):
        if itype not in ['info', 'error']:
            raise ValueError('Type can only be info or error')
        self.title = title
        self.items = items

    def __str__(self):
        return self.title

class ReturnChannel:
    def __init__(self, call_back, call_back_args={}):
        self.is_open = True
        self.call_back = call_back
        self.call_back_args = call_back_args
        self.info_container = Info

    def set_info_container(self, info_cls):
        self.info_container = info_cls

    def close(self):
        self.is_open = False

    def emit_obj(self, obj):
        if not self.is_open:
            raise ValueError('Emit operation on closed channel')
        self.call_back(obj, **self.call_back_args)

    def emit(self, *args, **kwargs):
        info = self.info_container(*args, **kwargs)
        logger.debug('Emitting Msg: %s' % str(info))
        self.emit_obj(info)

def load_modules():
    command = {}

    for mod_name in modules.__all__:
        if mod_name.startswith('_'):
            continue
        try:
            mod = __import__('sdetools.modules.' + mod_name)
        except ImportError:
            logging.exception('Exception in importing module %s' % (mod_name))
            raise commons.UsageError('Unable to import module %s' % (mod_name))
        mod = getattr(mod.modules, mod_name)
        if not hasattr(mod, 'Command'):
            raise commons.UsageError('Module missing Command class: %s' % (mod_name))
        cmd_cls = mod.Command
        if not hasattr(cmd_cls, 'name'):
            cmd_cls.name = mod_name
        if not hasattr(cmd_cls, 'help'):
            raise commons.UsageError('Missing help string for module %s' % (cmd_cls.name))
        command[cmd_cls.name] = cmd_cls

    return command

def run_command(cmd_name, args, call_src, call_options={},
        call_back=stdout_callback, call_back_args={}):

    command = load_modules()

    if cmd_name not in command:
        raise commons.UsageError("Command not found: %s" % (cmd_name))

    curr_cmd = command[cmd_name]

    ret_chn = ReturnChannel(call_back, call_back_args)
    config = conf_mgr.Config(command, args, ret_chn, call_src, call_options)

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

