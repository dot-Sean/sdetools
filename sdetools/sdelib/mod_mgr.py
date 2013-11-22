import logging
logger = logging.getLogger(__name__)

import conf_mgr
import commons

from sdetools import modules

def stdout_callback(obj):
    print obj

class Info(object):
    def __init__(self, ev_type, msg='', **items):
        if ev_type not in ['info', 'error', 'close']:
            raise ValueError('Type can only be info or error')
        self.ev_type = ev_type
        self.msg = msg
        self.items = items

    def __str__(self):
        ev_type = self.ev_type
        if ev_type == 'close':
            msg = 'Done - '
            if self.items['status']:
                msg += 'Success'
            else:
                msg += 'Failed'
            if self.msg:
                msg += ': %s' % self.msg
            return msg
        else:
            return '%s: %s' % (ev_type.title(), self.msg)

class EmitShortCut:
    def __init__(self, ret_chn):
        self.ret_chn = ret_chn
        self.info = self.ret_chn.emit_info
        self.error = self.ret_chn.emit_error
        self.close = self.ret_chn.close
        self.queue = self.ret_chn.queue

    def __call__(self, *args, **kwargs):
        self.ret_chn.emit_it(*args, **kwargs)

class ReturnChannel(object):
    def __init__(self, call_back, call_back_args={}):
        self.is_open = True
        self.call_back = call_back
        self.call_back_args = call_back_args
        self.info_container = Info
        self.emit = EmitShortCut(self)
        self.queued_objs = {}

    def set_info_container(self, info_cls):
        self.info_container = info_cls

    def emit_obj(self, obj):
        if not self.is_open:
            raise ValueError('Emit operation on closed channel')
        self.call_back(obj, **self.call_back_args)

    def emit_it(self, *args, **kwargs):
        kwargs = kwargs.copy()
        kwargs.update(self.queued_objs)
        self.queued_objs = {}
        info = self.info_container(*args, **kwargs)
        logger.debug('Emitting Msg: "%s"' % str(info))
        self.emit_obj(info)

    def queue(self, **kwargs):
        """
        It allows objects to be added to a dict
        Next emit will have these items attached and queue gets reset
        """
        self.queued_objs.update(kwargs)

    def close(self, *args, **kwargs):
        """
        Note that close always expects a status
        """
        if 'status' not in kwargs:
            raise ValueError('Missing status for close')
        self.emit_it('close', *args, **kwargs)
        self.is_open = False

    def emit_info(self, *args, **kwargs):
        self.emit_it('info', *args, **kwargs)

    def emit_error(self, *args, **kwargs):
        self.emit_it('error', *args, **kwargs)

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
        if not hasattr(cmd_cls, 'sub_cmds'):
            cmd_cls.sub_cmds = []
        command[cmd_cls.name] = cmd_cls

    return command

def run_command(cmd_name, args, call_src, call_options={},
        call_back=stdout_callback, call_back_args={}):

    # Split command and sub-command
    sub_cmd_name = None
    if '.' in cmd_name:
        cmd_name, sub_cmd_name = cmd_name.split('.', 1)

    command_list = load_modules()

    if cmd_name not in command_list:
        raise commons.UsageError("Command not found: %s" % (cmd_name))

    ret_chn = ReturnChannel(call_back, call_back_args)
    config = conf_mgr.Config(cmd_name, sub_cmd_name, command_list, args, ret_chn, call_src, call_options)

    curr_cmd = command_list[cmd_name]

    if sub_cmd_name is not None:
        if sub_cmd_name not in curr_cmd.sub_cmds:
            raise commons.UsageError("Sub-Command %s not found for command %s" % (sub_cmd_name, cmd_name))

    try:
        cmd_inst = curr_cmd(config, args)

        cmd_inst.configure()

        ret_status = cmd_inst.parse_args()

        cmd_inst.args = config.args
        cmd_inst.process_args()

        ret_status = cmd_inst.handle()
    except commons.Error, e:
        if call_src == 'shell':
            raise
        else:
            logger.exception(str(e))
        config.ret_chn.close(status=False, msg=str(e))
        return False

    config.ret_chn.close(status=True)

    if ret_status is None:
        ret_status = True
    return ret_status

