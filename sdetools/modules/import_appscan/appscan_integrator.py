import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError
from sdetools.modules.import_appscan.appscan_standard_xml_importer import AppScanStandardXMLImporter
from sdetools.modules.import_appscan.appscan_enterprise_xml_importer import AppScanEnterpriseXMLImporter
from sdetools.modules.import_appscan.appscan_zip_importer import AppScanZIPImporter

__all__ = ['AppScanIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'appscan', 'sde_appscan_map.xml')

class AppScanIntegrationError(IntegrationError):
    pass

class AppScanIntegrator(BaseIntegrator):
    TOOL_NAME = "appscan"
    VALID_PRODUCT_EDITIONS = ['standard', 'enterprise']

    def __init__(self, config):
        supported_file_types = ['xml', 'zip']
        super(AppScanIntegrator, self).__init__(config, self.TOOL_NAME, supported_file_types, DEFAULT_MAPPING_FILE)
        self.config.opts.add("edition", "AppScan edition, i.e. %s" % ','.join(AppScanIntegrator.VALID_PRODUCT_EDITIONS),
                             "e", "standard")

    def initialize(self):
        super(AppScanIntegrator, self).initialize()
        if self.config['edition'] not in AppScanIntegrator.VALID_PRODUCT_EDITIONS:
            raise UsageError("Unsupported AppScan edition: %s" % self.config['edition'])

        if self.config['edition'] == 'enterprise':
            self.weakness_map_identifier = 'title'

    def parse_report_file(self, report_file, report_type):
        if report_type == 'xml':
            if self.config['edition'] == 'standard':
                importer = AppScanStandardXMLImporter()
            elif self.config['edition'] == 'enterprise':
                importer = AppScanEnterpriseXMLImporter()
        elif report_type == 'zip':
            importer = AppScanZIPImporter(self.config['edition'])
        else:
            raise UsageError("Unsupported file type (%s)" % report_type)

        importer.parse(report_file)

        self.findings = importer.findings
        self.report_id = importer.id

        return importer.findings, importer.id

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.findings]
