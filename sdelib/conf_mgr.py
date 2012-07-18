import sys
import os
import optparse
import ConfigParser
import shlex

from commons import show_error

__all__ = ['config', 'Config']

#TODO: Add local config
DEFAULT_CONFIG_FILE = "~/.sdelint.cnf"

class Config:
    DEFAULTS = {
            'conf_file': DEFAULT_CONFIG_FILE,
            'interactive': True,
            'server': None,
            'method': 'https',   # Can be 'http' or 'https'
            'authmode': 'session', # Can be 'session' or 'basic'
            'email': None,
            'password': '', # A None for password means Ask for Password
            'application': None,
            'project': None,
            'skip_hidden': True,
            'debug': 0,
            'targets': None,
        }

    def __init__(self):
        self.settings = self.DEFAULTS.copy()

    def __getitem__(self, key):
        if key in self.settings:
            return self.settings[key]
        raise KeyError, 'Undefined configuration item: %s' % (key)

    def __setitem__(self, key, val):
        if key not in self.settings:
            raise KeyError, 'Unknown configuration item: %s' % (key)
        self.settings[key] = val

    def parse_config_file(self, file_name):
        if not file_name:
            return True, 'Empty file.'
        file_name = os.path.expanduser(file_name)

        cnf = ConfigParser.ConfigParser()
        # This will preserve case
        config.optionxform = str
        stat = cnf.read(file_name)
        if not stat:
            if (file_name == DEFAULT_CONFIG_FILE):
                return True, 'Missing default config file.'
            else:
                return False, 'Config file not found.'

        for key in ['debug', 'server', 'email', 'password', 'application', 'project', 'targets', 'authmode']:
            if cnf.has_option('global', key):
                val = cnf.get('global', key)
                if key == 'targets':
                    val = list(shlex.shlex(val, posix=True))
                if key == 'password':
                    if not val:
                        val = None
                self[key] = val
        return True, 'Config File Parsed'

    def parse_args(self, arvg):
        usage = "%prog [options...] target1 [target2 ...]\n\ntarget(s) are the directory/file to be scanned."

        parser = optparse.OptionParser(usage)
        parser.add_option('-c', '--config', metavar='CONFIG_FILE', dest='conf_file', default=self.DEFAULTS['conf_file'], type='string',
            help = "Configuration File if. Ignored if -C is used. (Default is %s)" % (self.DEFAULTS['conf_file']))
        parser.add_option('-C', '--skipconfig', dest='skip_conf_file', default=False, action='store_true',
            help = "Do NOT use any configuration file")
        parser.add_option('-I', '--noninteractive', dest='interactive', default=True, action='store_false', 
            help="Run in Non-Interactive mode")
        parser.add_option('-e', '--email', metavar='EMAIL', dest='email', default='', type='string',
            help = "Username for SDE Accout")
        parser.add_option('-p', '--password', metavar='PASSWORD', dest='password', default='', type='string',
            help = "Password for SDE Accout")
        parser.add_option('-P', '--askpasswd', dest='askpasswd', default=False, action='store_true',
            help = "Prompt for SDE Accout password (interactive mode only)")
        parser.add_option('-s', '--server', dest='server', default='', type='string', help="SDE Server instance to use")
        parser.add_option('-a', '--application', dest='application', default='', type='string', help="SDE Application to use")
        parser.add_option('-j', '--project', dest='project', default='', help="SDE Project to use")
        parser.add_option('-H', '--skiphidden', dest='skip_hidden', default=self.DEFAULTS['skip_hidden'], action='store_false',
            help = "Skip hidden files/directories.")
        parser.add_option('-d', '--debug', metavar='LEVEL', dest='debug', default=self.DEFAULTS['debug'], type='int',
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

        if (not opts.interactive) and (opts.askpasswd):
            show_error("Password can not be asked in Non-Interactive mode", usage_hint=True)
            return False

        if opts.skip_conf_file:
            self['conf_file'] = None
        else:
            self['conf_file'] = opts.conf_file

        ret_stat, ret_val = self.parse_config_file(self['conf_file'])
        if not ret_stat:
            show_error("Unable to read or process configuration file.\n Reason: %s" % (ret_val))
            return False

        if args:
            self['targets'] = args

        if not self['targets']:
            show_error("Missing target (e.g. use \".\" for current dir)", usage_hint=True)
            return False

        for path in self['targets']:
            if not os.path.exists(path):
                show_error("Unable to locate or access the path: %s" % path)
                return False

        # No more errors, lets apply the changes
        self['debug'] = opts.debug
        self['skip_hidden'] = opts.skip_hidden
        self['interactive'] = opts.interactive
        if opts.server:
            self['server'] = opts.server
        if not self['server']:
            show_error("Server not specified", usage_hint=True)
            return False
        if opts.email:
            self['email'] = opts.email
        if not self['email']:
            show_error("Email not specified", usage_hint=True)
            return False
        if opts.askpasswd:
            self['password'] = None
        else:
            if opts.password:
                self['password'] = opts.password
            if not self['password']:
                show_error("Password not specified", usage_hint=True)
                return False
        if opts.application:
            self['application'] = opts.application
        if opts.project:
            self['project'] = opts.project

        return True

config = Config()
