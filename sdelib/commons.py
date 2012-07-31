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
    password = getpass.getpass()
    # Handle Control-C or Control-Z
    if(password is not None and (password.find('\x03') >= 0 or password.find('\x1a') >= 0)):
        raise KeyboardInterrupt
    return password

