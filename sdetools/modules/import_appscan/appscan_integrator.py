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
    VALID_PRODUCT_EDITIONS = ['standard', 'enterprise', "auto"]

    def __init__(self, config):
        supported_file_types = ['xml', 'zip']
        self.AVAILABLE_IMPORTERS = [
            {
                'name': 'zip',
                'importer': AppScanZIPImporter()
            },
            {
                'name': 'standard',
                'importer': AppScanStandardXMLImporter()
            },
            {
                'name': 'enterprise',
                'importer': AppScanEnterpriseXMLImporter()
            }
        ]
        super(AppScanIntegrator, self).__init__(config, self.TOOL_NAME, supported_file_types, DEFAULT_MAPPING_FILE)
        self.config.opts.add("edition", "AppScan edition, i.e. %s" % ','.join(AppScanIntegrator.VALID_PRODUCT_EDITIONS),
                             "e", "auto")

    def initialize(self):
        super(AppScanIntegrator, self).initialize()
        if self.config['edition'] not in AppScanIntegrator.VALID_PRODUCT_EDITIONS:
            raise UsageError("Unsupported AppScan edition: %s" % self.config['edition'])

    def parse_report_file(self, report_file, report_type):

        if report_type == 'xml' and self.config['edition'] == 'standard':
            importer = AppScanStandardXMLImporter()
        elif report_type == 'xml' and self.config['edition'] == 'enterprise':
            importer = AppScanEnterpriseXMLImporter()
        else:
            importer = self.detect_importer(report_file)

        if not importer:
            raise UsageError("Unsupported or malformed file")

        if importer.edition == 'standard':
            self.weakness_map_identifier = 'id'
            self.set_tool_name('appscan')
        elif importer.edition == 'enterprise':
            self.weakness_map_identifier = 'title'
            self.set_tool_name('appscan_enterprise')

        # load the task -> weakness mapping
        self.load_mapping_from_xml()

        importer.parse(report_file)

        self.findings = importer.findings
        self.report_id = importer.id

        return importer.findings, importer.id

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.findings]
