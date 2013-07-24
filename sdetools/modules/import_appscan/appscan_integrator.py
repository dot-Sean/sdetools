import os
import re
from sdetools.extlib.defusedxml import minidom

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError

__all__ = ['FortifyIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(commons.media_path, 'appscan', 'sde_appscan_map.xml')

class AppScanIntegrationError(IntegrationError):
    pass

class AppScanIntegrator(BaseIntegrator):
    TOOL_NAME = "appscan"

    def __init__(self, config):
        config.add_custom_option("report_xml", "AppScan Report XML", "x", None)
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []

    def _make_raw_finding(self, node):
        entry = {}
        group_title = None
        weakness_count = 0
 
        try:
            group_title = node.getElementsByTagName("groupTitle")[0].firstChild.data
            weakness_count = int(node.attributes['count'].value)
        except Exception, e:       
            raise FortifyIntegrationError("Malformed GroupingSection detected in SubSection 'Issues By Category'")

        entry['id'] = group_title
        entry['description'] = group_title
        entry['count'] = weakness_count
        return entry

    def parse(self):
        try:
            base = minidom.parse(self.config['report_xml'])
        except KeyError, ke:
            raise FortifyIntegrationError("Missing configuration option 'report_xml'")
        except Exception, e:
            raise FortifyIntegrationError("Error opening report xml (%s)" % self.config['report_xml'])
              
        self.report_id = ""

        report_sections = base.getElementsByTagName('ReportSection')
        if not report_sections:
            raise FortifyIntegrationError("Malformed report detected: ReportSection not found")

        for report_section in report_sections:
            title = report_section.getElementsByTagName('Title')[0]
            if (title.firstChild.data == 'Issue Count by Category'):
                issue_listing = report_section.getElementsByTagName('IssueListing')[0]
                grouping_sections = issue_listing.getElementsByTagName('GroupingSection')
                for grouping_section in grouping_sections:
                    self.raw_findings.append( self._make_raw_finding(grouping_section) )
            elif (title.firstChild.data == 'Project Summary'):
                subsection = report_section.getElementsByTagName('SubSection')[0]
                subsection_text = subsection.getElementsByTagName('Text')[0]
                m = re.search('Build Label:\s*(.+)', subsection_text.firstChild.data)
                if m:
                    self.report_id = m.group(1)
                    
        if self.report_id == "":
            raise FortifyIntegrationError("Build Label not found" % self.config['report_xml'])

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count':item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
