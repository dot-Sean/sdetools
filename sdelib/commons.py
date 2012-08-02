__all__ = ['json', 'Error', 'show_error', 'get_password']

import getpass

try:
    import json
except ImportError:
    import json_compat as json

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
    print "FATAL ERROR: %s" % (err_msg)
    if usage_hint:
        print "Try -h to see the usage"
    print

def get_password():
    try:
        password = getpass.getpass()
    except EOFError:
        # Handle Ctrl+D
        raise KeyboardInterrupt
    if (password is None):
        return password
    # Handle Ctrl+C
    if '\x03' in password:
        raise KeyboardInterrupt
    # Handle Ctrl+Z
    if '\x1a' in password:
        raise KeyboardInterrupt
    return password

