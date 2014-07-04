from sdetools.sdelib.cmd import BaseCommand
from sdetools.modules.import_threadfix.threadfix_integrator import ThreadFixAPI, ThreadFixIntegrator

class Command(BaseCommand):
    help = 'ThreadFix -> SDE import utility.'

    def configure(self):
        tf_api = ThreadFixAPI(self.config)
        self.tf_integrator = ThreadFixIntegrator(tf_api, self.config)

    def handle(self):
        self.tf_integrator.initialize()
        self.tf_integrator.load_mapping_from_xml()
        self.tf_integrator.parse()
        self.emit.info('Finding file parsed successfully. Starting the import')
        self.tf_integrator.import_findings()