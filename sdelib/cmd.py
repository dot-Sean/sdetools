import commons

class BaseCommand(object):
    cmd_name = None

    def __init__(self, config):
        self.config = config

    def handle(self, *args):
        raise commons.UsageError('You can not use base class directly.')
