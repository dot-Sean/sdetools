import commons

class CommandBase(object):
    def __init__(self, config):
        self.config = config

    def handle(self, *args):
        raise commons.UsageError('You can not use base class directly.')
