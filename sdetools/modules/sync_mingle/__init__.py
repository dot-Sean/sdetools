from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase

class Command(BaseCommand):
    help = 'Mingle <-> SDE sync utility.'

    def configure(self):
        alm_api = MingleAPIBase(self.config)
        self.mingle = MingleConnector(self.config, alm_api)

    def handle(self):
        self.mingle.initialize()
        self.mingle.synchronize()
        return True
