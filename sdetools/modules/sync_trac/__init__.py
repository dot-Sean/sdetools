from sdetools.sdelib.cmd import BaseCommand

from sdetools.modules.sync_trac.trac_plugin import TracConnector, TracXMLRPCAPI

class Command(BaseCommand):
    help = 'Trac <-> SDE sync utility.'

    def configure(self):
        alm_api = TracXMLRPCAPI(self.config)
        self.trac = TracConnector(self.config, alm_api)

    def handle(self):
        self.trac.initialize()
        self.trac.synchronize()
        return True
