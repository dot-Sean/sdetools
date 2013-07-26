import os
import re

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError

from sdetools.modules.import_fortify.fortify_report_importer import FortifyReportImporter
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter


__all__ = ['FortifyIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(commons.media_path, 'fortify', 'sde_fortify_map.xml')

class FortifyIntegrationError(IntegrationError):
    pass

class FortifyIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        config.add_custom_option("report_xml", "Fortify Report XML", "x", None)
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []
        self.importer = None

    def parse(self):
    
        try:
            fileName, file_extension = os.path.splitext(self.config['report_xml'])
        except KeyError, ke:
            raise FortifyIntegrationError("Missing configuration option 'report_xml'")
        
        if file_extension == '.xml':
            self.importer = FortifyReportImporter()
        elif file_extension == '.fpr':
            self.importer = FortifyFPRImporter()
        elif file_extension == '.fvdl':
            self.importer = FortifyFVDLImporter()
        else:
            raise FortifyIntegrationError("Unsupported file type (%s)" % file_extension)

        self.importer.parse(self.config['report_xml'])
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id

        if self.report_id is None or self.report_id == "":
            raise FortifyIntegrationError("Report ID not found in report file (%s)" % self.config['report_xml'])

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count':item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]