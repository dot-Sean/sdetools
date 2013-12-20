#!/usr/bin/python
import sys

from sdetools.sdelib import commons
from sdetools.sdelib import mod_mgr
from sdetools.sdelib import log_mgr

log_mgr.setup_root_logger()

import logging
logger = logging.getLogger(__name__)

def main(argv):
    if len(argv) < 2:
        commons.show_error("Missing command", usage_hint=True)
        return False
    
    curr_cmd_name = None
    if '-h' in argv[1:]:
        curr_cmd_name = 'help'
        args = ['help', '-h']
    else:
        args = argv[1:]
        for arg in args:
            if not arg.startswith('-'):
                curr_cmd_name = arg
                break

    if not curr_cmd_name:
        commons.show_error("Missing command", usage_hint=True)
        return False

    try:
        exit_stat = mod_mgr.run_command(curr_cmd_name, args[1:], 'shell')
    except commons.UsageError, e:
        commons.show_error(str(e), usage_hint=True)
        return False
    except commons.Error, e:
        logger.exception(str(e))
        commons.show_error(str(e))
        return False

    return exit_stat

if __name__ == "__main__":
    exit_stat = main(sys.argv)
    if not exit_stat:
        sys.exit(1)
    else:
        sys.exit(0)
