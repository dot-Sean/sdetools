from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.import_fortify import fortify_integrator

class Command(BaseCommand):
    help = 'Fortify -> SDE import utility.'

    def configure(self):
        self.ft_integrator = fortify_integrator.FortifyIntegrator(self.config)

    def handle(self):
        self.ft_integrator.initialize()
        self.ft_integrator.load_mapping_from_xml()
        self.ft_integrator.parse()
        self.emit.info('Findings loaded successfully. Starting the import')
        self.ft_integrator.import_findings()
