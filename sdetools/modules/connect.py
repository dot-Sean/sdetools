import inspect
import urlparse

from sdetools.sdelib.commons import UsageError, json
from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib import sdeapi

def has_method(obj, name):
    v = vars(obj.__class__)
    # check if name is defined in obj's class and that name is a method
    return name in v and inspect.isroutine(v[name])

class Command(BaseCommand):
    help = 'Tests connectivity to SD Elements'

    def configure(self):
        self.api = sdeapi.APIBase(self.config)

    def list_functions(self):
        all_funcs = [x for x in dir(self.api) 
                if has_method(self.api, x) and not x.startswith('_')]
        return all_funcs

    def check_connection(self):
        try:
            result = self.api.connect()
        except self.api.APIError, err:
            return False, str(err)
        return True, 'Connection Successful'

    def handle(self):
        status, reason = self.check_connection() 

        self.emit.queue(status=status, msg=reason)
