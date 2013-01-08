# Copyright SDElements Inc
#
# Plugin for two way integration with Rally

from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.interactive_plugin import PluginError

class Command(BaseCommand):
    help = 'Rally <-> SDE sync utility.'

    def configure(self):
        rbase = RallyAPIBase(self.config)
        self.rally = RallyConnector(self.config, rbase)

    def handle(self):
        self.rally.initialize()
        self.rally.synchronize()
        return True
