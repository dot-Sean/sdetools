#!/usr/bin/python
#
# Ehsan Foroughi
# Copyright SDElements Inc
#

from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib.commons import show_error, Error, UsageError
from sdetools.sdelib.interactive_plugin import PlugInExperience
from sdetools.sdelib.scanner import Scanner

class Command(BaseCommand):
    name = 'lint'
    help = 'SDE Lint tool scans project file and displays tasks that match the context of each file.'
    conf_syntax = 'target1 [target2 ...]'
    conf_help = 'target(s) are the directory/file to be scanned.'

    def configure(self):
        self.scanner = Scanner(self.config)
        self.plugin = PlugInExperience(self.config)

    def process_args(self):
        if self.args:
            targets = self.args
        else:
            targets = self.config['args']
        err_reason = self.scanner.set_targets(targets)
        if err_reason:
            raise UsageError(err_reason)
        return True

    def handle(self):
        content = self.plugin.get_compiled_task_list()
            
        self.scanner.set_content(content)
        self.scanner.scan()
