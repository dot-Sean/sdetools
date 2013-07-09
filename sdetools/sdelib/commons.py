__all__ = ['json', 'Error', 'show_error', 'get_password', 'urlencode_str']

import sys
import os
import urllib

import getpass

try:
    import json
except ImportError:
    from sdetools.extlib import json_compat as json

try:
    import abc
except ImportError:
    from sdetools.extlib import abc_compat as abc

try:
    import argparse
except ImportError:
    from sdetools.extlib import argparse_compat as argparse

base_path = None
media_path = None

class Error(Exception):
    """
    Base Error for sdetools.
    All Exceptions in the tool must be inherited from this.
    """
    def __str__(self):
        return "FATAL ERROR: %s\n" % (self.args)

class UsageError(Error):
    """
    Wrong usage of library functions.
    E.g. invalid choices for arguments.
    """
    def __str__(self):
        return "UsageError: %s\n" % (self.args)

def setup_base_path(base_path_val):
    global base_path
    global media_path

    base_path = base_path_val
    media_path = os.path.join(base_path, 'docs')

def show_error(err_msg, usage_hint=False):
    sys.stderr.write(err_msg)
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

def urlencode_str(inp):
    return urllib.urlencode({'a':inp})[2:]
