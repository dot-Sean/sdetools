import sys
import os
import optparse

#TODO: Add local config
DEFAULT_CONFIG_FILE = "~/.sdelint.cnf"

class Config:
    DEFAULTS = {
            'targets': None,
            'debug_level': 0,
            'skip_hidden': True,
            'interactive': True,
            'askpasswd': False,
            'server': None,
            'username': None,
            'password': None,
            'application': None,
            'project': None,
        }

    def __init__(self):
        self.settings = self.DEFAULTS.copy()

    def __getitem__(self, key):
        if key in self.settings:
            return self.settings[key]
        raise KeyError, 'Undefined configuration item'

    def parse_args(self, arvg):
        usage = "%prog [options...] target1 [target2 ...]\n\ntarget(s) are the directory/file to be scanned."

        parser = optparse.OptionParser(usage)
        parser.add_option('-i', '--cnf', metavar='CONF_FILE', dest='cnf', 
            help = "Location of config file. Note that command line values bypass the values specified in the config file.", type='string')
        parser.add_option('-I', '--noninteractive', dest='interactive', default=True, action='store_false', help="Run in Non-Interactive mode")
        parser.add_option('-e', '--email', metavar='EMAIL', dest='username', default='', type='string',
            help = "Username for SDE Accout")
        parser.add_option('-p', '--password', metavar='PASSWORD', dest='password', default='', type='string',
            help = "Password for SDE Accout")
        parser.add_option('-P', '--askpasswd', dest='askpasswd', default=self.DEFAULTS['askpasswd'], action='store_true',
            help = "Prompt for SDE Accout password (interactive mode only)")
        parser.add_option('-s', '--server', dest='server', default='', help="SDE Server instance to use")
        parser.add_option('-a', '--application', dest='application', default='', help="SDE Application to use")
        parser.add_option('-j', '--project', dest='project', default='', help="SDE Project to use")
        parser.add_option('-H', '--skiphidden', dest='skip_hidden', default=self.DEFAULTS['skip_hidden'], action='store_false',
            help = "Skip hidden files/directories.")
        parser.add_option('-d', '--debug', metavar='LEVEL', dest='debug_level', default=self.DEFAULTS['debug_level'], type='int',
            help = "Set debug level (Default is 0, i.e. show no debug messages)")

        try:
            (opts, args) = parser.parse_args()
        except:
            if (str(sys.exc_info()[1]) == '0'):
                # This happens when -h is used
                return False
            else:
                show_error("Invalid options specified.", usage_hint=True)
                return False

        if (len(args) < 1):
            show_error("Missing target (e.g. use \".\" for current dir)", usage_hint=True)
            return False

        for path in args:
            if not os.path.exists(path):
                show_error("Unable to locate or access the path: %s" % path)
                return False

        if (not opts.interactive) and (opts.askpasswd):
            show_error("Password can not be asked in Non-Interactive mode", usage_hint=True)
            return False

        # No more errors, lets apply the changes
        self.settings['targets'] = args
        self.settings['debug_level'] = opts.debug_level
        self.settings['skip_hidden'] = opts.skip_hidden
        self.settings['interactive'] = opts.interactive
        self.settings['askpasswd'] = opts.askpasswd
        self.settings['server'] = opts.server
        self.settings['username'] = opts.username
        self.settings['password'] = None
        if not opts.askpasswd:
            self.settings['password'] = opts.password
        self.settings['application'] = opts.application
        self.settings['project'] = opts.project

        return True

config = Config()
