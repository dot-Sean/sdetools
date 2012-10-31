# Copyright SDElements Inc
#
# Plugin for two way integration with JIRA

from sdelib.cmd import BaseCommand
from sdelib.interactive_plugin import PlugInExperience
from modules.sync_jira.jira_plugin import JIRAConnector, JIRAAPIBase
from modules.sync_jira.jira_plugin import add_jira_config_options
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError


class Command(BaseCommand):
    help = 'JIRA <-> SDE sync utility.'

    def configure(self):
        add_jira_config_options(self.config)

    def handle(self):
        try:
            sde_plugin = PlugInExperience(self.config)
            jbase = JIRAPIABase(self.config)
            jira = JIRAConnector(sde_plugin, jbase)
            jira.synchronize()
        except (AlmException, PluginError), err:
            print 'The following error was encountered: %s' % err
            return False
        return True
