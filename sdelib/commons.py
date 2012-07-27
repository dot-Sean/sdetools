__all__ = ['json', 'Error', 'show_error']

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
