#!/usr/bin/python
#
# Version 0.5
# Ehsan Foroughi
# Copyright SDElements Inc
#

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.commons import show_error
from sdelib.interactive_plugin import PlugInExperience
from sdelib.scanner import Scanner

"""
    def read_config(self):
        import ConfigParser
        cnf = ConfigParser.ConfigParser()
        cnf.read(self.config['cnf'])
        self.ID = cnf.get('mysqld', 'server-id')
"""

def load():
    plugin = PlugInExperience(config)

    ret_err, ret_val = plugin.get_compiled_task_list()
    if ret_err:
        show_error('Unexpected Error - code %s: %s' % (ret_err, ret_val))
        sys.exit(1)
        
    content = ret_val
    scanner = Scanner(config, content)
    scanner.scan()

def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    load()

if __name__ == "__main__":
    main(sys.argv)

