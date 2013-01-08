import inspect
import urlparse

from sdetools.sdelib.commons import UsageError, json
from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib.apiclient import APIBase

def has_method(obj, name):
    v = vars(obj.__class__)
    # check if name is defined in obj's class and that name is a method
    return name in v and inspect.isroutine(v[name])

class Command(BaseCommand):
    help = 'Call SD Elements API'

    def configure(self):
        self.api = APIBase(self.config)
        self.config.add_custom_option("api_func", "API Function to be Called", "f", None)
        self.config.add_custom_option("api_args", "API Arguments in URL Encoded format (skip if empty)", "a", '')

    def list_functions(self):
        all_funcs = [x for x in dir(self.api) 
                if has_method(self.api, x) and not x.startswith('_')]
        return all_funcs

    def handle(self):
        all_funcs = self.list_functions()
        if self.config['api_func'] not in all_funcs:
            raise UsageError('Invalid function: %s\nAvailable choices are:\n  %s\n' % 
                    (self.config['api_func'], '\n  '.join(all_funcs)))
        
        try:
            args = urlparse.parse_qs(self.config['api_args'])
        except:
            raise UsageError('Unable to URL Dcode value: %s' % (self.config['api_args'][:200]))
            
        ret = getattr(self.api, self.config['api_func'])(**args)

        print json.dumps(ret)
        return

