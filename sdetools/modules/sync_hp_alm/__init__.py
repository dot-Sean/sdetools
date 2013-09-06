# Copyright SDElements Inc
#
# Plugin for two way integration with HP ALM

from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.sync_hp_alm.hp_alm_plugin import HPAlmConnector, HPAlmAPIBase
from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.sdelib.interactive_plugin import PluginError

class Command(BaseCommand):
    help = 'HP Alm <-> SDE sync utility.'

    def configure(self):
        rbase = HPAlmAPIBase(self.config)
        self.hp_alm = HPAlmConnector(self.config, rbase)

    def handle(self):
        self.hp_alm.initialize()
        self.hp_alm.synchronize()
        return True
