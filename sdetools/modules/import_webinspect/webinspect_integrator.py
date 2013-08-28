import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError
from sdetools.modules.import_webinspect.webinspect_xml_importer import WebInspectXMLImporter

from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

__all__ = ['WebInspectIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'webinspect', 'sde_webinspect_map.xml')

class WebInspectIntegrationError(IntegrationError):
    pass

class WebInspectIntegrator(BaseIntegrator):
    TOOL_NAME = "webinspect"

    def __init__(self, config):
        config.add_custom_option("report_file", "WebInspect Report File", "x", None)
        config.add_custom_option("report_type", "WebInspect Report Type: xml|auto", default="auto")
        super(WebInspectIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []

    def parse(self):

        if not self.config['report_file']:
            raise UsageError("Missing configuration option 'report_file'")

        if self.config['report_type'] == 'auto': 
            if not isinstance(self.config['report_file'], basestring):
                raise UsageError("On auto-detect mode, the file name needs to be specified.")
            fileName, file_extension = os.path.splitext(self.config['report_file'])
            self.config['report_type'] = file_extension[1:]

        if self.config['report_type'] == 'xml':
            self.importer = WebInspectXMLImporter()
        else:
            raise UsageError("Unsupported file type (%s)" % self.config['report_type'])

        self.importer.parse(self.config['report_file'])
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id

        if self.importer.report_id:
            self.report_id = self.importer.report_id
        else:
            self.emit.info("Report ID not found in report: Using default.")

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'type': item['type']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
