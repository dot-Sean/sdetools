#!/usr/bin/python
#
# Version 0.5
# Ehsan Foroughi
# Copyright SDElements Inc
#

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.commons import show_error, json, Error
from sdelib.interactive_plugin import PlugInExperience
from sdelib.scanner import Scanner

def load():
    plugin = PlugInExperience(config)

    content = plugin.get_compiled_task_list()
        
    scanner = Scanner(config, content)
    scanner.scan()

def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    try:
        load()
    except Error, e:
        show_error(str(e))

if __name__ == "__main__":
    main(sys.argv)

