# Copyright SDElements Inc
#
# Plugin for two way integration with Rally

from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase


class Command(BaseCommand):
    help = 'Rally <-> SDE sync utility.'

    def configure(self):
        alm_api = RallyAPIBase(self.config)
        self.rally = RallyConnector(self.config, alm_api)

    def handle(self):
        self.rally.initialize()
        self.rally.synchronize()
        return True
