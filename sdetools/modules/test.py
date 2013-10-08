import sys
import traceback
import unittest

from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib import commons

class Command(BaseCommand):
    name = 'test'
    help = 'Runs tests for one or all modules.'
    conf_syntax = '[module_name]'
    conf_help = 'command_name: [optional] Specify a module to be tested\n'\
        '  (omit to run test for all modules)'

    def configure(self):
        self.test_mod = None

    def parse_args(self):
        if self.args:
            self.test_mod = self.args[0]
            if self.test_mod not in self.config.command_list:
                raise commons.UsageError('Unable to find command %s' % (self.test_mod))
        return True

    def import_test(self, mod_name):
        try:
            mod = __import__('sdetools.modules.%s.tests' % mod_name)
        except ImportError:
            return False
        test_mod = getattr(mod.modules, mod_name).tests
        print 'Importing tests for: %s' % mod_name
        if hasattr(test_mod, '__all__'):
            for test_class in test_mod.__all__:
                try:
                    __import__('sdetools.modules.%s.tests.%s' % (mod_name, test_class))
                except:
                    print '  ***** Unable to import from %s.tests.%s' % (mod_name, test_class)
                    print traceback.format_exc()
                    continue
                print '  - importing tests from %s.tests.%s' % (mod_name, test_class)
        return True

    def handle(self):
        self.suite = unittest.TestLoader()
        if self.test_mod:
            res = self.import_test(self.test_mod)
            if not res:
                raise commons.UsageError('Module %s is missing tests' % self.test_mod)
        else:
            for mod_name in sorted(self.config.command_list):
                res = self.import_test(mod_name)
                if not res:
                    print '-> Module missing tests: %s' % mod_name

        unittest.TextTestRunner(verbosity=2).run(self.suite)
        return True

