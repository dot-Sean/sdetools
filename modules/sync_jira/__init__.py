# Copyright SDElements Inc
#
# Plugin for two way integration with JIRA

from sdelib.cmd import BaseCommand
from modules.sync_jira.jira_plugin import JIRAConnector, JIRAAPIBase
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError


class Command(BaseCommand):
    help = 'JIRA <-> SDE sync utility.'

    def configure(self):
        jbase = JIRAAPIBase(self.config)
        self.jira = JIRAConnector(self.config, jbase)

    def handle(self):
        try:
            self.jira.initialize()
            self.jira.synchronize()
        except (AlmException, PluginError), err:
            print 'The following error was encountered: %s' % err
            return False
        return True
