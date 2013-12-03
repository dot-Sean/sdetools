from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_appscan.appscan_xml_importer import AppScanXMLImporter

class AppScanZIPImporter(BaseZIPImporter):

    def __init__(self):
        super(AppScanZIPImporter, self).__init__()
        self.register_importer('appscan.xml', AppScanXMLImporter())


    def parse(self, zip_file):
        self.process_archive(zip_file)
        self.findings = self.IMPORTERS['appscan.xml'].findings
        self.id = self.IMPORTERS['appscan.xml'].id
