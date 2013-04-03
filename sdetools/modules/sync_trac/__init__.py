from sdetools.sdelib.cmd import BaseCommand

from sdetools.modules.sync_trac.trac_plugin import TracConnector, TracXMLRPCAPI

class Command(BaseCommand):
    help = 'Trac <-> SDE sync utility.'

    def configure(self):
        mbase = TracXMLRPCAPI(self.config)
        self.trac = TracConnector(self.config, mbase)

    def handle(self):
        self.trac.initialize()
        self.trac.synchronize()
        return True
