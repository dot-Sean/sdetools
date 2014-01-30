#!/usr/bin/python
#
# Ehsan Foroughi
# Copyright SDElements Inc
#
import re

from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib import commons

SEARCH_CMD_RE = re.compile(r'^[a-zA-Z0-9_^$]*$')

class Command(BaseCommand):
    help = 'Compiles a complete configuration object for all modules.'
    conf_syntax = '[search_cmd]'
    conf_help = 'search_cmd: [optional] Specify a substring to filter commands that are included\n'\
        '  (omit to see a list of available commands)'

    def configure(self):
        self.config.opts.add(
            'match_cmd', 
            "Specify a substring to filter commands that are included (use ^ and $ to match start and end)",
            default='')

    def handle(self):
        if not SEARCH_CMD_RE.match(self.config['match_cmd']):
            raise commons.UsageError('Invalid match_cmd. Needs to have only a-z A-Z 0-9 ^ and &')
        search_re = re.compile(self.config['match_cmd'])

        all_opts = {}

        cmd_list = self.config.command_list.keys()
        cmd_list.sort()
        for cmd in cmd_list:
            if not search_re.match(cmd):
                continue

            cmd_obj = self.config.command_list[cmd]
            cmd_config = self.config.copy(cmd, cmd_obj.sub_cmds[0])
            cmd_inst = cmd_obj(cmd_config, [])
            cmd_inst.configure()
            cmd_inst.config.import_custom_options()

            all_opts[cmd] = []
            for sub_cmd in cmd_inst.sub_cmds:
                subcmd_opts = {
                    'name': sub_cmd,
                    'opts': cmd_config.opts[sub_cmd],
                    }
                all_opts[cmd].append(subcmd_opts)

        self.emit.queue(all_opts=all_opts)
        
        return True
