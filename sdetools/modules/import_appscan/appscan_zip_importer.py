from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_appscan.appscan_standard_xml_importer import AppScanStandardXMLImporter
from sdetools.modules.import_appscan.appscan_enterprise_xml_importer import AppScanEnterpriseXMLImporter


class AppScanZIPImporter(BaseZIPImporter):

    def __init__(self):
        super(AppScanZIPImporter, self).__init__()
        self.available_importers = [
            {
                'name': 'standard',
                'pattern': '^.+\.xml$',
                'importer': AppScanStandardXMLImporter()
                }, {
                'name': 'enterprise',
                'pattern': '^.+\.xml$',
                'importer': AppScanEnterpriseXMLImporter()
            }
        ]
        self.edition = None

