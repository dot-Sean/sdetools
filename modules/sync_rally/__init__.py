# Copyright SDElements Inc
#
# Plugin for two way integration with Rally

from sdelib.cmd import BaseCommand
from sdelib.interactive_plugin import PlugInExperience
from modules.sync_jira.lib.jira_plugin import RallyConnector, RallyAPIBase
from modules.sync_jira.lib.jira_plugin import add_rally_config_options
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError

class Command(BaseCommand):
    help = 'Rally <-> SDE sync utility.'

    def configure(self):
        add_rally_config_options(self.config)

    def handle(self):
        try:
            sde_plugin = PlugInExperience(self.config)
            rbase = RallyAPIBase(self.config)
            rally = JIRAConnector(sde_plugin, rbase)
            rally.synchronize()
        except (AlmException, PluginError), err:
            print 'The following error was encountered: %s' % err
            return False
        return True
