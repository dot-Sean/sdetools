from sdelib.cmd import BaseCommand
from mod_import_veracode import veracode_integrator

class Command(BaseCommand):
    help = 'Veracode -> SDE import utility.'

    def customize_config(self):
        self.vc_integrator = veracode_integrator.VeracodeIntegrator(self.config)

    def handle(self, *args):
        self.vc_integrator.load_mapping_from_xml()
        self.vc_integrator.parse()
        self.vc_integrator.import_findings()
