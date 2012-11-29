#!/usr/bin/python
#
# Version 0.5
# Ehsan Foroughi
# Copyright SDElements Inc
#

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdelib.conf_mgr import config
from sdelib.commons import show_error, Error
from sdelib.interactive_plugin import PlugInExperience

def load():
    plugin = PlugInExperience(config)

    plugin.get_compiled_task_list()
        
    plugin.add_task_ide_note("T21","Test note","filename","DONE")

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

