# Copyright SDElements Inc
#
# Plugin for two way integration with HP ALM

from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.sync_hp_alm.hp_alm_plugin import HPAlmConnector, HPAlmAPIBase


class Command(BaseCommand):
    help = 'HP Alm <-> SDE sync utility.'

    def configure(self):
        alm_api = HPAlmAPIBase(self.config)
        self.hp_alm = HPAlmConnector(self.config, alm_api)

    def handle(self):
        self.hp_alm.initialize()
        self.hp_alm.synchronize()
        return True
