from sdetools.analysis_integration.base_integrator import BaseZIPImporter
from sdetools.modules.import_appscan.appscan_standard_xml_importer import AppScanStandardXMLImporter
from sdetools.modules.import_appscan.appscan_enterprise_xml_importer import AppScanEnterpriseXMLImporter

class AppScanZIPImporter(BaseZIPImporter):

    def __init__(self, appscan_edition):
        super(AppScanZIPImporter, self).__init__()
        if appscan_edition == 'standard':
            self.register_importer_for_pattern('^.+\.xml$', AppScanStandardXMLImporter())
        elif appscan_edition == 'enterprise':
            self.register_importer_for_pattern('^.+\.xml$', AppScanEnterpriseXMLImporter())
        else:
            raise ValueError('Invalid appscan_edition: %s' % appscan_edition)