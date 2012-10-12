# Copyright SDElements Inc
#
# Plugin for two way integration with JIRA

from sdelib.interactive_plugin import PlugInExperience
from jira_integration.lib.jira_plugin import JIRAConnector
from jira_integration.lib.jira_plugin import JIRABase, add_jira_config_options
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError


class Command(BaseCommand):
    help = 'JIRA <-> SDE sync utility.'

    def customize_config(self):
        add_jira_config_options(self.config)

    def handle(self, *args):
        try:
            sde_plugin = PlugInExperience(self.config)
            jbase = JIRABase(self.config)
            jira = JIRAConnector(sde_plugin, jbase)
            jira.synchronize()
        except (AlmException, PluginError), err:
            print 'The following error was encountered: %s' % err

