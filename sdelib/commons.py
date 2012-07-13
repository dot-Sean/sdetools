__all__ = ['show_error', 'json']

try:
    import json
except ImportError:
    import json_compat as json

def show_error(err_msg, usage_hint=False):
    print "FATAL ERROR: %s" % (err_msg)
    if usage_hint:
        print "Try -h to see the usage"
    print
