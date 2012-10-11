#!/usr/bin/python
#
# Ehsan Foroughi
# Copyright SDElements Inc
#

from sdelib.cmd import BaseCommand
from sdelib.conf_mgr import config
from sdelib.commons import show_error, Error
from sdelib.interactive_plugin import PlugInExperience
from sdelib.scanner import Scanner

class Command(BaseCommand):
    help = 'SDE Lint tool scans project file and displays tasks that match the context of each file.'

    def handle(self, *args):
        scanner = Scanner(config)

        ret = config.parse_args(argv)
        if not ret:
            sys.exit(1)

        try:
            plugin = PlugInExperience(config)

            content = plugin.get_compiled_task_list()
                
            scanner.set_content(content)
            scanner.scan()
            load(scanner)
        except Error, e:
            show_error(str(e))

