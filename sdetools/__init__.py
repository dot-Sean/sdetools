__all__ = [
    'call',
    'sdelib', 
    'modules', 
    'alm_integration', 
    'extlib',
]

def setup_docs_path():
    import sys
    import os

    if sys.platform.startswith("win"):
        current_file = sys.argv[0]
    else:
        current_file = __file__
    BASE_PATH = os.path.split(os.path.abspath(current_file))[0]

    from sdetools.sdelib import commons
    commons.base_path = BASE_PATH

setup_docs_path()

def call(cmd_name, args):
    from sdetools.sdelib import mod_mgr

    exit_stat = mod_mgr.run_command(cmd_name, args, 'import')

    return exit_stat
