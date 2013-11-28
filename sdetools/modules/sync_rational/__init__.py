from sdetools.sdelib.cmd import BaseCommand

from sdetools.extlib.oslc_consumer import OSLCAPI
from sdetools.modules.sync_rational.rational_plugin import RationalConnector, RationalAPI

class Command(BaseCommand):
    help = 'Rational CLM <-> SDE sync utility.'

    def configure(self):
        sync_base = OSLCAPI(self.config)
        self.alm = RationalConnector(self.config, sync_base)

    def handle(self):
        self.alm.initialize()
        self.alm.synchronize()
        return True
