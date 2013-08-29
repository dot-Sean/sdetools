from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_appscan.appscan_xml_importer import AppScanXMLImporter

class AppScanZIPImporter(BaseZIPImporter):
    ARCHIVED_FILE_NAME = "appscan.xml"

    def __init__(self):
        super(AppScanZIPImporter, self).__init__()

    def parse(self, zip_file):

        self.process_archive(zip_file, AppScanXMLImporter())
