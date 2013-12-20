#!/usr/bin/python
#
# Ehsan Foroughi
# Copyright SDElements Inc
#
import sys

from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib import commons

class Command(BaseCommand):
    name = 'help'
    help = 'Prints the list of available commands.'
    conf_syntax = '[command_name]'
    conf_help = 'command_name: [optional] Specify command name for help\n'\
        '  (omit to see a list of available commands)'

    def configure(self):
        self.help_cmd = None
        self.help_subcmd = None

    def parse_args(self):
        # We bypass parsing and validation of args by overwriting the base class behavior
        # This is unique to help
        if not self.args:
            return True

        if '-h' in self.args:
            self.config.parse_args(self)
            return False

        self.help_cmd = self.args[0]
        if '.' in self.help_cmd:
            self.help_cmd, self.help_subcmd = self.help_cmd.split('.', 1)

        if self.help_cmd not in self.config.command_list:
            raise commons.UsageError('Unable to find command %s' % (self.help_cmd))
        if not self.help_subcmd:
            self.help_subcmd = self.config.command_list[self.help_cmd].sub_cmds[0]
        if self.help_subcmd not in self.config.command_list[self.help_cmd].sub_cmds:
            raise commons.UsageError('Unable to find subcommand %s' % (self.help_subcmd))
        return True

    def get_commands_help(self):
        ret = []
        for cmd_name in self.config.command_list:
            ret.append((cmd_name, self.config.command_list[cmd_name].help))
        ret.sort()
        return ret

    def print_command_list(self, cmd_list):
        print 'Available commands are:'
        print
        for cmd_name, cmd_help in cmd_list:
            print '%s%s' % (cmd_name.ljust(20), cmd_help)
        print
        print 'Hint: %s help COMMAND -> See the help for commands' % (sys.argv[0])
        print

    def handle(self):
        if self.help_cmd:
            cmd_obj = self.config.command_list[self.help_cmd]
            
            cmd_config = self.config.copy(self.help_cmd, self.help_subcmd)

            cmd_inst = cmd_obj(cmd_config, self.args)
            cmd_inst.configure()
            cmd_inst.config.import_custom_options()
            cmd_inst.config.prepare_parser(cmd_inst)
            cmd_inst.config.parser.print_help()
        else:
            cmd_list = self.get_commands_help()
            self.print_command_list(cmd_list)

        return True
