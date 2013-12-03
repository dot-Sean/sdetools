import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError
from sdetools.modules.import_appscan.appscan_xml_importer import AppScanXMLImporter
from sdetools.modules.import_appscan.appscan_zip_importer import AppScanZIPImporter

__all__ = ['AppScanIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'appscan', 'sde_appscan_map.xml')

class AppScanIntegrationError(IntegrationError):
    pass

class AppScanIntegrator(BaseIntegrator):
    TOOL_NAME = "appscan"

    def __init__(self, config):
        supported_file_types = ['xml', 'zip']
        super(AppScanIntegrator, self).__init__(config, self.TOOL_NAME, supported_file_types, DEFAULT_MAPPING_FILE)

    def parse_report_file(self, report_file, report_type):
        if report_type == 'xml':
            importer = AppScanXMLImporter()
        elif report_type == 'zip':
            importer = AppScanZIPImporter()
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
