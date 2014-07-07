from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.import_whitehat.whitehat_integrator import WhiteHatAPI, WhiteHatIntegrator

class Command(BaseCommand):
    help = 'WhiteHat -> SDE import utility.'

    def configure(self):
        wh_api = WhiteHatAPI(self.config)
        self.wh_integrator = WhiteHatIntegrator(wh_api, self.config)

    def handle(self):
        self.wh_integrator.initialize()
        self.wh_integrator.load_mapping_from_xml()
        self.wh_integrator.parse()
        self.emit.info('Finding file parsed successfully. Starting the import')
        self.wh_integrator.import_findings()