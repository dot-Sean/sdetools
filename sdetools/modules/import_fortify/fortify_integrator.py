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
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)

        config.add_custom_option('integration_mode',"Integration mode: (ssc or file)", default='file')
        config.add_custom_option("file_results", "Verification results file", "x", default='')
        config.add_custom_option('ssc_test_connection','Test Fortify SSC Connection Only '
                '(Also checks existence of project and version)', default='False')
        config.add_custom_option('ssc_method','http vs https for Fortify SSC server', default='https')
        config.add_custom_option('ssc_server','Fortify SSC server name or IP', default='')
        config.add_custom_option('ssc_user','Fortify SSC user',default='')
        config.add_custom_option('ssc_pass','Fortify SSC password',default='')
        config.add_custom_option('ssc_project_name','Fortify Project name',default='')
        config.add_custom_option('ssc_project_version','Fortify Project version',default='')
        
        self.raw_findings = []
        self.importer = None

    def initialize(self):
        super(FortifyIntegrator, self).initialize()
        
        if self.config['integration_mode'] == 'ssc':
            self.config.process_boolean_config('ssc_test_connection')

            config_keys = ['ssc_method','ssc_server','ssc_user','ssc_pass','ssc_project_name','ssc_project_version']
            for config_key in config_keys:
                if not self.config[config_key]:
                    raise commons.UsageError("Missing value for option %s" % config_key)

        elif self.config['integration_mode'] == 'file':        
            if not self.config['file_results']:
                raise commons.UsageError("Missing value for option file_results")
        else:
            raise commons.UsageError("Invalid value for integration_mode. Valid values are: ssc or file")
            
    def start(self):

        if self.config['integration_mode'] == 'file':
            try:
                fileName, file_extension = os.path.splitext(self.config['file_results'])
            except KeyError, ke:
                raise FortifyIntegrationError("Missing configuration option 'file_results'")

            if file_extension == '.xml':
                self.importer = FortifyReportImporter()
            elif file_extension == '.fpr':
                self.importer = FortifyFPRImporter()
            elif file_extension == '.fvdl':
                self.importer = FortifyFVDLImporter()
            else:
                raise FortifyIntegrationError("Unsupported file type (%s)" % file_extension)

            self.importer.parse(self.config['file_results'])
            
        elif self.config['integration_mode'] == 'ssc':
            self.importer = FortifySSCImporter(self.config)
            self.importer.run()
        
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id

        if not self.report_id:
            raise FortifyIntegrationError("Report ID not found in report file (%s)" % self.config['file_results'])

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
