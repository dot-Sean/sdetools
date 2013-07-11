import os
import re
from xml.dom import minidom

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError

__all__ = ['WebInspectIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(commons.media_path, 'fortify', 'sde_fortify_map.xml')

class WebInspectIntegrationError(IntegrationError):
    pass

class WebInspectIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        config.add_custom_option("report_xml", "WebInspect Report XML", "x", None)
        super(WebInspectIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []

    def _make_raw_finding(self, node):
        entry = {}
        for classification in node.getElementsByTagName("Classification"):
            if classification.attributes['kind'].value == 'CWE':
                entry['type'] = 'cwe'
                entry['id'] = classification.attributes['identifier'].value
                return entry
        return entry

    def parse(self):
        try:
            base = minidom.parse(self.config['report_xml'])
        except KeyError, ke:
            raise WebInspectIntegrationError("Missing configuration option 'report_xml'")
        except Exception, e:
            raise WebInspectIntegrationError("Error opening report xml (%s)" % self.config['report_xml'])
              
        self.report_id = "Not defined"

        issues = base.getElementsByTagName('Issue')
        for issue in issues:
            self.raw_findings.append( self._make_raw_finding(issue) )
        urls = base.getElementsByTagName('URL')
        if urls:
            self.report_id = urls[0].firstChild.data

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'type': entry['type']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]