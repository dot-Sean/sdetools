from sdetools.sdelib.cmd import BaseCommand

from sdetools.modules.sync_pt.pt_plugin import PivotalTrackerConnector, PivotalTrackerAPI

class Command(BaseCommand):
    help = 'PivotalTracker <-> SDE sync utility.'

    def configure(self):
        sync_base = PivotalTrackerAPI(self.config)
        self.alm = PivotalTrackerConnector(self.config, sync_base)

    def handle(self):
        self.alm.initialize()
        self.alm.synchronize()
        return True
