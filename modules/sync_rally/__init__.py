# Copyright SDElements Inc
#
# Plugin for two way integration with Rally

from sdelib.cmd import BaseCommand
from modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError

class Command(BaseCommand):
    help = 'Rally <-> SDE sync utility.'

    def configure(self):
        rbase = RallyAPIBase(self.config)
        self.rally = RallyConnector(self.config, rbase)

    def handle(self):
        try:
            self.rally.initialize()
            self.rally.synchronize()
        except (AlmException, PluginError), err:
            print 'The following error was encountered: %s' % err
            return False
        return True
