#!/usr/bin/python
#
# Version 0.5
# Ehsan Foroughi
# Copyright SDElements Inc
#

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.commons import show_error, Error
from sdetools.sdelib.interactive_plugin import PlugInExperience


def load():
    plugin = PlugInExperience(Config)

    plugin.get_compiled_task_list()
        
    plugin.add_task_note("T21", "Test note", "filename", "DONE")


def main(argv):
    ret = Config.parse_args(argv)
    if not ret:
        sys.exit(1)

    try:
        load()
    except Error, e:
        show_error(str(e))

if __name__ == "__main__":
    main(sys.argv)

