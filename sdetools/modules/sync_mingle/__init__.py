from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase

class Command(BaseCommand):
    help = 'Mingle <-> SDE sync utility.'

    def configure(self):
        mbase = MingleAPIBase(self.config)
        self.mingle = MingleConnector(self.config, mbase)

    def handle(self):
        self.mingle.initialize()
        self.mingle.synchronize()
        return True
