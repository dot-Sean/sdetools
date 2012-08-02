#!/usr/bin/python
#
# Version 0.5
# Ehsan Foroughi
# Copyright SDElements Inc
#

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdelib.conf_mgr import config
from sdelib.commons import show_error, json, Error
from sdelib.interactive_plugin import PlugInExperience
from sdelib.scanner import Scanner

def load(scanner):
    plugin = PlugInExperience(config)

    content = plugin.get_compiled_task_list()
        
    scanner.set_content(content)
    scanner.scan()

def main(argv):
    scanner = Scanner(config)

    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    try:
        load(scanner)
    except Error, e:
        show_error(str(e))

if __name__ == "__main__":
    main(sys.argv)

