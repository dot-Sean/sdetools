import sys
import os
import optparse
import ConfigParser
import shlex
import logging
import datetime

import log_mgr
logger = log_mgr.mods.add_mod(__name__)

from sdetools.sdelib.commons import UsageError, json

__all__ = ['Config']

DEFAULT_CONFIG_FILE = os.path.join("~", ".sdelint.cnf")

LOG_LEVELS = {
    'debug': logging.DEBUG,
    'verbose': logging.INFO,
    'default': logging.WARNING,
    'error': logging.ERROR,
    'quiet': logging.CRITICAL,
    }

class Option(object):
    """
    Use this to extend the options for your own use cases. The item is added to arguments.
    The same var_name is parsed from config file if present.

    Args:
        var_name: Name of the config variable. (use lower case, numbers and underscore)
        help_title: A one or two sentence description of the config item
        [short_form]: a single character where (e.g. 'w' for -w)
        [default]: Optional. Emtpy string by default
        [meta_var]: Optional. Defaults to capital format
        [group_name]: Name of the group (use same name for grouping)

    Note: the long form becomes --<var_name>
    Note: short form is case sensitive
    Note: Do not use the base <var_names> (used in the base defaults)
    Note: If default is a string, the option is optional. Otherwise, it is mandatory.
    """
    def __init__(self, var_name, help_title, short_form=None,
                default='', meta_var=None, group_name=None):
        var_name = var_name.lower()

        self.var_name = var_name
        self.help_title = help_title
        self.short_form = short_form
        self.default = default
        self.meta_var = meta_var
        self.group_name = group_name

    def __str__(self):
        summary = {}
        for item in [
                'var_name', 'help_title', 'short_form', 'default',
                'meta_var', 'group_name']:
            summary[item] = getattr(self, item)
        return str(summary)

    def __repr__(self):
        return '%s(**%s)' % (self.__class__.__name__, str(self))

class ModuleOptions(dict):
    """
    Note: The first item in sub_cmds is the default.
    """

    Option = Option

    def __init__(self, sub_cmds=['']):
        self.sub_cmds = sub_cmds
        for sub_cmd in self.sub_cmds:
            self[sub_cmd] = []

    def add(self, *args, **kwargs):
        opt = self.Option(*args, **kwargs)
        self.add_opt(opt)

    def add_subcmd(self, sub_cmd, *args, **kwargs):
        opt = self.Option(*args, **kwargs)
        self.add_opt(opt, sub_cmd)

    def add_opt(self, opt, sub_cmd=None):
        # Note: sub_cmd being '' vs None have two different meanings here
        if sub_cmd is None:
            for cmd in self:
                self[cmd].append(opt)
        else:
            if sub_cmd not in self:
                raise UsageError("Sub-Command %s is not available" % sub_cmd)
            self[sub_cmd].append(opt)

    def copy(self):
        dup = ModuleOptions()
        for item in self:
            dup[item] = self[item]
        return dup

class Config(object):
    """
    The Configuration class. The module creates a singleton instance by default.
    However, this class can be instantiated, modified /customized, and passed to 
    the plugin class during instantiation. This way, several configurations can
    be used in the same execution without singleton limitations.

    Note: This is a non interactive module. Convention: Use default value None to 
    indicate that a value needs to be asked interactively.

    Usage sample:
        prj_name = config['sde_project']
    """
    DEFAULTS = {
            'conf_file': DEFAULT_CONFIG_FILE,
            'interactive': True,
            # Can be 'api_token'|'session'|'basic'
            'authmode': 'api_token', 
            'application': None,
            'project': None,
            'skip_hidden': True,
            'log_level': logging.WARNING,
            'debug_mods': '',
            'args': None,
            'proxy_auth': '',
        }

    def __init__(self, cmd_name, sub_cmd_name, command_list, args, ret_chn, call_src, call_options={}):
        if call_src not in ['shell', 'import']:
            raise UsageError("Invalid config source")

        self.command_list = command_list
        self.command = cmd_name
        self.sub_cmds = self.command_list[self.command].sub_cmds
        self.opts = ModuleOptions(self.sub_cmds)
        self.sub_cmd = sub_cmd_name
        self.args = args[1:]

        self.call_src = call_src
        self.settings = self.DEFAULTS.copy()
        self.custom_options = []
        self.parser = None
        self.use_conf_file = True
        self.call_options = call_options
        self.ret_chn = ret_chn
        self.emit = self.ret_chn.emit

    def copy(self, command=None, sub_cmd=''):
        copy_opts = False
        if command is None:
            command = self.command
            sub_cmd = self.sub_cmd
            copy_opts = True
        dup = Config(command, sub_cmd, self.command_list, [''] + self.args, self.ret_chn,
                self.call_src, self.call_options)
        dup.use_conf_file = self.use_conf_file
        if copy_opts:
            dup.settings = self.settings.copy()
            dup.opts = self.opts.copy()
        return dup

    def __getitem__(self, key):
        if key in self.settings:
            return self.settings[key]
        raise KeyError, 'Undefined configuration item: %s' % (key)

    def __setitem__(self, key, val):
        if key not in self.settings:
            raise KeyError, 'Unknown configuration item: %s' % (key)
        self.settings[key] = val

    def has_key(self, key):
        return key in self.settings

    __contains__ = has_key

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def import_custom_options(self, opt_list=None, rebuild=False):
        if opt_list is None:
            opt_list = self.opts
        if rebuild:
            self.settings = self.DEFAULTS.copy()
        for opt in opt_list[self.sub_cmd]:
            self._add_custom_option(opt.var_name, opt.help_title, opt.short_form,
                    opt.default, opt.meta_var, opt.group_name)

    def _add_custom_option(self, var_name, help_title, short_form=None, 
            default='', meta_var=None, group_name=None):
        if var_name in self.settings:
            logger.warning('Attempting to re-customize an existing '
                'config %s (IGNORE)' % var_name)
            return

        if type(default) is str:
            help_title += ' [optional]'
            if default:
                help_title += ' default: %s' % (default)

        config_item = {
            'var_name': var_name,
            'help_title': help_title,
            'default': default,
            'meta_var': meta_var,
            'long_form': '--' + var_name,
        }
        if short_form:
            config_item['short_form'] = '-' + short_form

        if config_item['meta_var'] is None:
            config_item['meta_var'] = var_name.upper()
        self.settings[var_name] = config_item['default']

        if not group_name:
            group_name = "Module-specific option"
        for name, optlist in self.custom_options:
            if group_name == name:
                optlist.append(config_item)
                return
        self.custom_options.append((group_name, [config_item]))

    def parse_config_file(self, file_name):
        if not file_name:
            return True, 'Empty file.'
        file_name = os.path.expanduser(file_name)

        cnf = ConfigParser.ConfigParser()
        # This will preserve case
        cnf.optionxform = str
        if file_name == '-':
            cnf.readfp(sys.stdin)
        else:
            stat = cnf.read(file_name)
            if not stat:
                if file_name == os.path.expanduser(DEFAULT_CONFIG_FILE):
                    return True, 'Missing default config file.'
                else:
                    return False, 'Config file not found.'

        config_keys = ['log_level', 'debug_mods', 'application', 'project', 
            'authmode', 'args', 'proxy_auth']

        for name, optlist in self.custom_options:
            for item in optlist:
                config_keys.append(item['var_name'])

        for key in config_keys:
            if not cnf.has_option('global', key):
                continue
            val = cnf.get('global', key)
            if key == 'args':
                val = list(shlex.shlex(val, posix=True))
            elif key == 'password':
                if not val:
                    val = None
            elif key == 'log_level':
                val = val.strip()
                if val not in LOG_LEVELS:
                    return False, 'Unknown log_level value in config file'
                val = LOG_LEVELS[val]
            self[key] = val
        return True, 'Config File Parsed'

    def prepare_parser(self, cmd_inst):
        usage = "%%prog %s [Options] %s\n" % (cmd_inst.name, cmd_inst.conf_syntax)
        if cmd_inst.conf_help:
            usage += '%s\n' % (cmd_inst.conf_help)
        usage += "\n Hint: %prog help -> List commands\n"
        usage += " Hint: %%prog help %s -> Providers help for command %s" %\
            (cmd_inst.name, cmd_inst.name)

        parser = optparse.OptionParser(usage)
        self.parser = parser
        if self.use_conf_file:
            parser.add_option('-c', '--config', metavar='CONFIG_FILE', dest='conf_file', 
                default=self.DEFAULTS['conf_file'], type='string',
                help = "Specify the configuration file to be used. (Default is %s)" % (self.DEFAULTS['conf_file']))
            parser.add_option('-C', '--skipconfig', dest='skip_conf_file', default=False, action='store_true',
                help = "Do NOT use any configuration file")
        parser.add_option('-I', '--noninteractive', dest='interactive', default=True, action='store_false', 
            help="Run in Non-Interactive mode")
        parser.add_option('-d', '--debug', dest='debug', action='store_true', 
            help = "Set logging to debug level")
        parser.add_option('-v', '--verbose', dest='verbose', action='store_true', help = "Verbose output")
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', 
            help = "Silent output (except for unrecoverable errors)")
        parser.add_option('--proxy_auth', metavar='USERNAME:PASSWORD', dest='proxy_auth', default='', type='string',
            help = "Proxy authentication credentials, in <username>:<password> format [optional]")
        parser.add_option('--debugmods', metavar='MOD_NAME1,[MOD_NAME2,[...]]', dest='debug_mods', 
            default='', type='string',
            help = "Comma-seperated List of modules to debug, e.g. sdetools.sdelib.sdeapi)")

        for group_name, optslist in self.custom_options:
            group = optparse.OptionGroup(parser, group_name)
            for item in optslist:
                opt_args = {
                    'dest': item['var_name'], 
                    'metavar': item['meta_var'], 
                    'type': 'string', 
                    'help': item['help_title']}
                opt_forms = [item['long_form']]
                if 'short_form' in item:
                    opt_forms.append(item['short_form'])
                group.add_option(*opt_forms, **opt_args)
            parser.add_option_group(group)

    def parse_args(self, cmd_inst):
        if self.call_src == 'shell':
            return self.parse_shell_args(cmd_inst)
        elif self.call_src == 'import':
            return self.parse_func_args(cmd_inst)

    def parse_func_args(self, cmd_inst):
        self['conf_file'] = None
        self['interactive'] = False
        for key in self.call_options:
            self[key] = self.call_options[key]
        #TODO: Perform validation

    def parse_shell_args(self, cmd_inst):
        if self.parser is None:
            self.prepare_parser(cmd_inst)

        try:
            (opts, args) = self.parser.parse_args()
        except:
            if (str(sys.exc_info()[1]) == '0'):
                # This happens when -h is used
                sys.exit(0)
            else:
                raise UsageError("Invalid options specified.")

        if (not self.use_conf_file) or opts.skip_conf_file:
            self['conf_file'] = None
        else:
            self['conf_file'] = opts.conf_file

        ret_stat, ret_val = self.parse_config_file(self['conf_file'])
        if not ret_stat:
            raise UsageError("Unable to read or process configuration file.\n Reason: %s" % (ret_val))

        # No more errors, lets apply the changes
        if opts.quiet:
            self['log_level'] = logging.CRITICAL
        if opts.verbose:
            self['log_level'] = logging.INFO
        if opts.debug:
            self['log_level'] = logging.DEBUG
        if opts.debug_mods:
            self['debug_mods'] = opts.debug_mods
        if type(self['debug_mods']) is str:
            self['debug_mods'] = [x.strip() for x in self['debug_mods'].split(',')]

        log_mgr.mods.set_all_level(self['log_level'])
        for modname in self['debug_mods']:
            log_mgr.mods.set_level(modname, logging.DEBUG)
            
        self['interactive'] = opts.interactive
        if (self['interactive']) and (self['conf_file'] == '-'):
            raise UsageError("Unable to use interactive mode with standard input for configuration: Use -I")
        if opts.proxy_auth:
            self['proxy_auth'] = opts.proxy_auth
        if self['proxy_auth']:
            self.fix_proxy_env()

        for group_name, optlist in self.custom_options:
            for item in optlist:
                name = item['var_name']
                val = getattr(opts, name)
                if val:
                    self[name] = val

                # Check for missing mandatory options
                if type(self[name]) is not str:
                    raise UsageError("Missing value for option '%s'" % (name))

    def fix_proxy_env(self):
        import urllib
        proxy_settings = urllib.getproxies()
        for ptype in proxy_settings:
            proxy = proxy_settings[ptype]
            if '://' not in proxy:
                proxy = '%s://%s' % (ptype, proxy)
            protocol, val = proxy.split('://')
            proxy = '%s://%s@%s' % (protocol, self['proxy_auth'], val)
            os.environ['%s_proxy' % ptype] = proxy

    def process_boolean_config(self, key):
        if self[key] in [True, False]:
            return
        self[key] = (str(self[key]).lower() == 'true')

    def process_list_config(self, key):
        if not self[key]:
            self[key] = []
            return
        if isinstance(self[key], basestring):
            self[key] = [x.strip() for x in self[key].split(',')]

    def process_json_str_dict(self, key):
        try:
            if not self[key]:
                self[key] = {}
            elif isinstance(self[key], basestring):
                self[key] = json.loads(self[key])
            if type(self[key]) is not dict:
                raise TypeError('Not a dictionary: %s' % self[key])
            for name in self[key]:
                if not isinstance(name, basestring):
                    raise TypeError('Invalid key for %s: %s' % (key, str(name)))
                val = self[key][name]
                if not isinstance(val, basestring):
                    raise TypeError('Invalid value for %s: %s' % (key, repr(val)))
        except Exception, err:
            raise UsageError('Unable to process %s (not a JSON dictionary). Reason: %s' % (key, str(err)))

    def process_date_config(self, key):
        if not isinstance(self[key], basestring):
            return
        try:
            self[key] = datetime.datetime.strptime(self[key], '%Y-%m-%d').date()
        except ValueError, err:
            raise UsageError('Unable to read date field %s. Reason: %s' % (key, str(err)))
