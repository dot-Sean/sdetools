import os

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator

from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError
from sdetools.modules.import_fortify.fortify_report_importer import FortifyReportImporter
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter

__all__ = ['FortifyIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'fortify', 'sde_fortify_map.xml')


class FortifyIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        config.opts.add("report_file", "Fortify Report File", "x", None)
        config.opts.add("report_type", "Fortify Report Type: xml|fpr|fvdl|auto", default="auto")
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []
        self.importer = None

    def parse(self):
        if not self.config['report_file']:
            raise UsageError("Missing configuration option 'report_file'")

        if self.config['report_type'] == 'auto': 
            if not isinstance(self.config['report_file'], basestring):
                raise UsageError("On auto-detect mode, the file name needs to be specified.")
            file_name, file_extension = os.path.splitext(self.config['report_file'])
            self.config['report_type'] = file_extension[1:]

        if self.config['report_type'] == 'xml':
            self.importer = FortifyReportImporter()
        elif self.config['report_type'] == 'fpr':
            self.importer = FortifyFPRImporter()
        elif self.config['report_type'] == 'fvdl':
            self.importer = FortifyFVDLImporter()
        else:
            raise FortifyIntegrationError("Unsupported file type (%s)" % self.config['report_type'])

        self.importer.parse(self.config['report_file'])
        self.raw_findings = self.importer.raw_findings

        if self.importer.report_id:
            self.report_id = self.importer.report_id
        else:
            self.emit.info("Report ID not found in report: Using default.")

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
