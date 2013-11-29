import commons

class BaseCommand(object):
    cmd_name = None
    conf_syntax = ''
    conf_help = ''
    sub_cmds = ['']

    def __init__(self, config, args):
        self.config = config
        self.emit = self.config.emit
        self.args = args
        self.opts = self.config.ModuleOptions(self.sub_cmds)

    def add_opt(self, *args, **kwargs):
        opt = self.opts.Option(*args, **kwargs)
        self.opts.add_opt(opt)

    def add_sub_opt(self, sub_cmd, *args, **kwargs):
        opt = self.opts.Option(*args, **kwargs)
        self.opts.add_opt(opt, sub_cmd)

    def configure(self):
        pass

    def parse_args(self):
        res = self.config.parse_args(self)
        if res:
            self.args = self.config.args
        return res

    def process_args(self):
        return True

    def handle(self):
        raise commons.UsageError('You can not use base class directly.')
