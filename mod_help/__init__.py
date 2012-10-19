#!/usr/bin/python
#
# Ehsan Foroughi
# Copyright SDElements Inc
#

from sdelib.cmd import BaseCommand
from sdelib.commons import show_error, Error
from sdelib.interactive_plugin import PlugInExperience
from sdelib.scanner import Scanner

class Command(BaseCommand):
    name = 'help'
    help = 'Prints the list of available commands.'

    def get_commands_help(self, command):
        ret = []
        for cmd_name in command:
            ret.append((cmd_name, command[cmd_name].help))
        ret.sort()
        return ret

    def print_command_list(self, cmd_list):
        print 'Available commands are:'
        print
        for cmd_name, cmd_help in cmd_list:
            print '%s%s' % (cmd_name.ljust(20), cmd_help)
        print

    def handle(self, *args):
        cmd_list = self.get_commands_help(self.config.command_list)
        self.print_command_list(cmd_list)
        return True

