from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.import_webinspect import webinspect_integrator

class Command(BaseCommand):
    help = 'Webinspect -> SDE import utility.'

    def configure(self):
        self.wi_integrator = webinspect_integrator.WebInspectIntegrator(self.config)

    def handle(self):
        self.wi_integrator.load_mapping_from_xml()
        self.wi_integrator.parse()
        self.emit.info('Finding file parsed successfully. Starting the import')
        self.wi_integrator.import_findings()
