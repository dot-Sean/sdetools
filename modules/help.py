#!/usr/bin/python
#
# Ehsan Foroughi
# Copyright SDElements Inc
#
import sys

from sdelib.cmd import BaseCommand
from sdelib import commons

class Command(BaseCommand):
    name = 'help'
    help = 'Prints the list of available commands.'

    def configure(self):
        self.config.set_custom_args('command', 'COMMAND: command name.',
            '    See help for list of available commands')
        if not self.args:
            return
        cmd_name = self.args[0]
        if cmd_name == self.name:
            return
        if cmd_name not in self.config.command_list:
            raise commons.UsageError('Error: Unable to find command %s' % (cmd_name))
        cmd_obj = self.config.command_list[cmd_name]
        cmd_inst = cmd_obj(self.config, self.args)
        cmd_inst.configure()
        ret = cmd_inst.config.parse_args(sys.argv)
        cmd_inst.config.parser.print_help()

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
        if self.args:
            return True
        cmd_list = self.get_commands_help()
        self.print_command_list(cmd_list)
        return True

