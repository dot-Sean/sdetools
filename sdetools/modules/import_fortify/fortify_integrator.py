import os
import datetime
import urllib2
import httplib

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseIntegrator

from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError
from sdetools.modules.import_fortify.fortify_report_importer import FortifyReportImporter
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter
from sdetools.modules.import_fortify.fortify_ssc_importer import FortifySSCImporter


__all__ = ['FortifyIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(commons.media_path, 'fortify', 'sde_fortify_map.xml')


class FortifyIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        config.add_custom_option('integration_mode',"Integration mode ('api' or 'file')", default='file')
        config.add_custom_option("result_file", "Verification results file", "x", None)
        config.add_custom_option('ssc_method','ss', default='')
        config.add_custom_option('ssc_server','sx', default='')
        config.add_custom_option('ssc_user','sy',default='')
        config.add_custom_option('ssc_pass','sz',default='')
        config.add_custom_option('ssc_project_name','Project name',default='')
        config.add_custom_option('ssc_project_version','Project version',default='')
        
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []
        self.importer = None

    def start(self):

        if self.config['integration_mode'] == 'file':
            try:
                fileName, file_extension = os.path.splitext(self.config['result_file'])
            except KeyError, ke:
                raise FortifyIntegrationError("Missing configuration option 'result_file'")

            if file_extension == '.xml':
                self.importer = FortifyReportImporter()
            elif file_extension == '.fpr':
                self.importer = FortifyFPRImporter()
            elif file_extension == '.fvdl':
                self.importer = FortifyFVDLImporter()
            else:
                raise FortifyIntegrationError("Unsupported file type (%s)" % file_extension)

            self.importer.parse(self.config['result_file'])
            
        elif self.config['integration_mode'] == 'api':
            self.importer = FortifySSCImporter(self.config)
            self.importer.run()
        
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id

        if not self.report_id:
            raise FortifyIntegrationError("Report ID not found in report file (%s)" % self.config['result_file'])

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
