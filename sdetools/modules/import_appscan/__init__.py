from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.import_appscan import appscan_integrator

class Command(BaseCommand):
    help = 'AppScan -> SDE import utility.'

    def configure(self):
        self.as_integrator = appscan_integrator.AppScanIntegrator(self.config)

    def handle(self):
        self.as_integrator.initialize()
        self.as_integrator.load_mapping_from_xml()
        self.as_integrator.load_custom_mapping_from_xml()
        self.as_integrator.parse()
        self.emit.info('Finding file parsed successfully. Starting the import')
        self.as_integrator.import_findings()
