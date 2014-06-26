import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError
from sdetools.modules.import_webinspect.webinspect_xml_importer import WebInspectXMLImporter
from sdetools.modules.import_webinspect.webinspect_fpr_importer import WebInspectFPRImporter

__all__ = ['WebInspectIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'webinspect', 'sde_webinspect_map.xml')


class WebInspectIntegrationError(IntegrationError):
    pass


class WebInspectIntegrator(BaseIntegrator):
    TOOL_NAME = "webinspect"

    def __init__(self, config):
        supported_file_types = ['xml', 'fpr']
        super(WebInspectIntegrator, self).__init__(config, self.TOOL_NAME, supported_file_types, DEFAULT_MAPPING_FILE)

    def parse_report_file(self, report_file, report_type):
        if report_type == 'xml':
            importer = WebInspectXMLImporter()
        elif report_type == 'fpr':
            importer = WebInspectFPRImporter()
        else:
            raise UsageError("Unsupported file type (%s)" % report_type)

        importer.parse(report_file)

        self.findings = importer.findings
        self.report_id = importer.id

        return importer.findings, importer.id

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'type': item['type']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.findings]
