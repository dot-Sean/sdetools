import re

from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib.commons import Error, UsageError
from sdetools.sdelib.restclient import APIError
from sdetools.sdelib.interactive_plugin import PlugInExperience
from sdetools.alm_integration.alm_plugin_base import AlmConnector


class Command(BaseCommand):
    help = 'Search and replace text in task notes'
    sde_plugin = None

    def configure(self):
        self.sde_plugin = PlugInExperience(self.config)

        self.config.opts.add('search_string', "Search string to find in a task note")
        self.config.opts.add('replace_string', "Replacement string")

    def sde_connect(self):
        if not self.sde_plugin:
            raise Error('Requires initialization')
        try:
            self.sde_plugin.connect()
        except APIError, err:
            raise Error('Unable to connect to SD Elements. Please review URL, id,'
                    ' and password in configuration file. Reason: %s' % (str(err)))

    def handle(self):
        if not self.config['search_string']:
            raise UsageError('Missing value for search_string')
        if not self.config['replace_string']:
            raise UsageError('Missing value for replace_string')

        self.sde_connect()
        tasks = self.sde_plugin.get_task_list()
        for task in tasks:
            task_notes = self.sde_plugin.get_task_notes(AlmConnector._extract_task_id(task['id']))
            if 'ide' in task_notes:
                for note in task_notes['ide']:
                    new_note_text = re.sub(self.config['search_string'], self.config['replace_string'], note['text'])
                    if new_note_text != note['text']:
                        self.sde_plugin.update_task_ide_note(note['id'], new_note_text)
            if 'text' in task_notes:
                for note in task_notes['text']:
                    new_note_text = re.sub(self.config['search_string'], self.config['replace_string'], note['text'])
                    if new_note_text != note['text']:
                        self.sde_plugin.update_task_text_note(note['id'], new_note_text)

        return True