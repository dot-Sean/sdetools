from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.import_veracode import veracode_integrator

class Command(BaseCommand):
    help = 'Veracode -> SDE import utility.'

    def configure(self):
        self.vc_integrator = veracode_integrator.VeracodeIntegrator(self.config)

    def handle(self):
        self.vc_integrator.load_mapping_from_xml()
        self.vc_integrator.parse()
        self.emit.info('Finding file parsed successfully. Starting the import')
        self.vc_integrator.import_findings()
