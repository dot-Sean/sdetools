import commons

class BaseCommand(object):
    cmd_name = None

    def __init__(self, config, args):
        self.config = config
        self.args = args

    def configure(self):
        pass

    def handle(self):
        raise commons.UsageError('You can not use base class directly.')
