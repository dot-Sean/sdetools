from sdetools.sdelib.cmd import BaseCommand

from sdetools.modules.sync_github.github_plugin import RationalConnector, RationalAPI

class Command(BaseCommand):
    help = 'Rational CLM <-> SDE sync utility.'

    def configure(self):
        sync_base = RationalAPI(self.config)
        self.alm = RationalConnector(self.config, sync_base)

    def handle(self):
        self.alm.initialize()
        self.alm.synchronize()
        return True
