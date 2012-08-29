import sys
import os
import optparse
import ConfigParser
import shlex
import logging

import log_mgr

from commons import show_error

__all__ = ['config', 'Config']

DEFAULT_CONFIG_FILE = "~/.sdelint.cnf"

LOG_LEVELS = {
    'debug': logging.DEBUG,
    'verbose': logging.INFO,
    'default': logging.WARNING,
    'error': logging.ERROR,
    'queit': logging.CRITICAL,
    }

class Config(object):
    """
    The Configuration class. The module creates a singleton instance by default.
    However, this class can be instantiated, modified /customized, and passed to 
    the plugin class during instantiation. This way, several configurations can
    be used in the same execution without singleton limitations.

    Note: This is a non interactive module. Convention: Use default value None to 
    indicate that a value needs to be asked interactively.

    Usage sample:
        prj_name = config['project']
    """
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
            'log_level': logging.WARNING,
            'debug_mods': '',
        }

    def __init__(self):
        self.settings = self.DEFAULTS.copy()
        self.custom_options = []
        self.custom_args = {
            'var_name': None,
            'syntax_text': '',
            'help_text': '',
            'validator_func': None,
            'validator_args': {},
        }

    def __getitem__(self, key):
        if key in self.settings:
            return self.settings[key]
        raise KeyError, 'Undefined configuration item: %s' % (key)

    def __setitem__(self, key, val):
        if key not in self.settings:
            raise KeyError, 'Unknown configuration item: %s' % (key)
        self.settings[key] = val

    def add_custom_option(self, var_name, help_title, short_form, default='', meta_var=None):
        """
        Use this to extend the options for your own use cases. The item is added to arguments.
        The same var_name is parsed from config file if present.

        Args:
            <var_name>: Name of the config variable. (use lower case, numbers and underscore only)
            <help_title>: A one or two sentence description of the config item.
            <short_form>: a single character where -<short_form> becomes the option (e.g. 'w' for -w).
            [<default>]: Optional. Emtpy string by default.
            [<meta_var>]: Optional. Defaults to capital format.

        Note: the long form becomes --<var_name>
        Note: short form is case sensitive
        Note: Do not use the base <var_names> (used in the base defaults)
        """
        config_item = {
            'var_name': var_name.lower(),
            'help_title': help_title,
            'default': default,
            'meta_var': meta_var,
            'short_form': '-' + short_form,
            'long_form': '--' + var_name.lower(),
        }

        if config_item['meta_var'] is None:
            config_item['meta_var'] = config_item['var_name'].upper()

        self.custom_options.append(config_item)
        self.settings[config_item['var_name']] = config_item['default']

    def set_custom_args(self, var_name, syntax_text, help_text, validator_func, validator_args={}):
        """
        Use this to tell the config manager to use the command arguments.
        Args:
            <var_name>: Name of the config variable. (use lower case, numbers and underscore only)
            <syntax_text>: The text for syntax of the arguments (e.g. target [option1])
            <help_text>: A multi-line capable blob of text help
            <validator_func>: A callback function to validate the arguments
                Syntax: myfunc(config, args, **<validator_args>)
                Return: None => Pass, <Error String> => Fail
            [<validator_args>]: A set of arguments to pass to validator function for state-keeping
        
        Note: The special variable in config is parsed the exact same way 
            a command line is parsed (quotes and what not)
        Note: Arguments are useful specially in the case where a list of input is passed to it
        """
        self.custom_args['var_name'] = var_name.lower()
        self.custom_args['syntax_text'] = syntax_text
        self.custom_args['help_text'] = help_text
        self.custom_args['validator_func'] = validator_func
        self.custom_args['validator_args'] = validator_args
        self.settings[self.custom_args['var_name']] = None

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

        config_keys = ['log_level', 'debug_mods', 'server', 'email', 'password', 
            'application', 'project', 'authmode']
        if self.custom_args['var_name']:
            config_keys.append(self.custom_args['var_name'])

        for item in self.custom_options:
            config_keys.append(item['var_name'])

        for key in config_keys:
            if cnf.has_option('global', key):
                val = cnf.get('global', key)
                if key == self.custom_args['var_name']:
                    val = list(shlex.shlex(val, posix=True))
                if key == 'password':
                    if not val:
                        val = None
                elif key == 'log_level':
                    val = val.strip(' ')
                    if val not in LOG_LEVELS:
                        return False, 'Unknown log_level value in config file'
                    val = LOG_LEVELS[val]
                self[key] = val
        return True, 'Config File Parsed'

    def parse_args(self, arvg):
        usage = "%%prog [options...] %s\n\n%s\n" % (self.custom_args['syntax_text'], self.custom_args['help_text'])

        parser = optparse.OptionParser(usage)
        parser.add_option('-c', '--config', metavar='CONFIG_FILE', dest='conf_file', 
            default=self.DEFAULTS['conf_file'], type='string',
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
        parser.add_option('-s', '--server', dest='server', default='', type='string', 
            help="SDE Server instance to use")
        parser.add_option('-a', '--application', dest='application', default='', type='string', 
            help="SDE Application to use")
        parser.add_option('-j', '--project', dest='project', default='', help="SDE Project to use")
        parser.add_option('-H', '--skiphidden', dest='skip_hidden', 
            default=self.DEFAULTS['skip_hidden'], action='store_false',
            help = "Skip hidden files/directories.")
        parser.add_option('-d', '--debug', dest='debug', action='store_true', 
            help = "Set logging to debug level")
        parser.add_option('-v', '--verbose', dest='verbose', action='store_true', help = "Verbose output")
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', 
            help = "Silent output (except for unrecoverable errors)")
        parser.add_option('--debugmods', metavar='MOD_NAME1,[MOD_NAME2,[...]]', dest='debug_mods', 
            default='', type='string',
            help = "Comma-seperated List of modules to debug, e.g. sdelib.apiclient)")
        for item in self.custom_options:
            parser.add_option(
                item['short_form'], item['long_form'], dest=item['var_name'], metavar=item['meta_var'], 
                default=item['default'], type='string', help=item['help_title'])

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
            show_error("Password can not be requested in Non-Interactive mode", usage_hint=True)
            return False

        if opts.skip_conf_file:
            self['conf_file'] = None
        else:
            self['conf_file'] = opts.conf_file

        ret_stat, ret_val = self.parse_config_file(self['conf_file'])
        if not ret_stat:
            show_error("Unable to read or process configuration file.\n Reason: %s" % (ret_val))
            return False

        if (self.custom_args['var_name'] is None):
            if args:
                show_error("Unknown arguments in the command line.", usage_hint=True)
                return False
        else:
            if args:
                self[self.custom_args['var_name']] = args
            ret = self.custom_args['validator_func'](
                self,
                self[self.custom_args['var_name']],
                **self.custom_args['validator_args'])
            if ret:
                show_error(ret, usage_hint=True)
                return False

        # No more errors, lets apply the changes
        if opts.quiet:
            self['log_level'] = logging.CRITICAL
        if opts.verbose:
            self['log_level'] = logging.INFO
        if opts.debug:
            self['log_level'] = logging.DEBUG
        if opts.debug_mods:
            self['debug_mods'] = opts.debug_mods
        self['debug_mods'] = [x.strip(' ') for x in self['debug_mods'].split(',')]

        log_mgr.mods.set_all_level(self['log_level'])
        for modname in self['debug_mods']:
            log_mgr.mods.set_level(modname, logging.DEBUG)
            
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

        for item in self.custom_options:
            name = item['var_name']
            val = getattr(opts, name)
            if val:
                self[name] = val

        return True

config = Config()
