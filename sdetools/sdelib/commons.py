__all__ = ['json', 'Error', 'show_error', 'get_password']

import sys

import getpass

try:
    import json
except ImportError:
    from extlib import json_compat as json

try:
    import abc
except ImportError:
    from extlib import abc_compat as abc

try:
    import argparse
except ImportError:
    from extlib import argparse_compat as argparse

base_path = None

class Error(Exception):
    """
    Base Error for the Lint Library.
    All Exceptions in the tool must be inherited from this.
    """
    pass

class UsageError(Error):
    """
    Wrong usage of library functions.
    E.g. invalid choices for arguments.
    """
    pass

def show_error(err_msg, usage_hint=False):
    sys.stderr.write("FATAL ERROR: %s\n" % (err_msg))
    if usage_hint:
        sys.stderr.write("  Try specifying 'help' as arguments to see the usage\n")

def get_password():
    try:
        password = getpass.getpass()
    except EOFError:
        # Handle Ctrl+D
        raise KeyboardInterrupt
    # Handle Ctrl+C and Ctrl+Z
    if password and ('\x03' in password or '\x1a' in password):
        raise KeyboardInterrupt
    return password

