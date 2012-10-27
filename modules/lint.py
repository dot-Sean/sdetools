#!/usr/bin/python
#
# Ehsan Foroughi
# Copyright SDElements Inc
#

from sdelib.cmd import BaseCommand
from sdelib.commons import show_error, Error, UsageError
from sdelib.interactive_plugin import PlugInExperience
from sdelib.scanner import Scanner

class Command(BaseCommand):
    name = 'lint'
    help = 'SDE Lint tool scans project file and displays tasks that match the context of each file.'
    conf_syntax = 'target1 [target2 ...]'
    conf_help = 'target(s) are the directory/file to be scanned.'

    def configure(self):
        self.scanner = Scanner(self.config)
        self.plugin = PlugInExperience(self.config)

    def process_args(self):
        err_reason = self.scanner.validate_args(self.args)
        if err_reason:
            raise UsageError(err_reason)
        return True

    def handle(self):
        content = self.plugin.get_compiled_task_list()
            
        self.scanner.set_content(content)
        self.scanner.scan()
