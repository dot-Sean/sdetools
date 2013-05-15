import os
from xml.dom import minidom

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError

__all__ = ['FortifyIntegrator']

REQUIRED_NODES = ['Category', 'cweid', 'categoryid', 'categoryname', 'description', 'severity', 'module','remediation_status']
LOCATION_ATTRIBS = ['sourcefilepath', 'sourcefile', 'line', 'location']

DEFAULT_MAPPING_FILE = os.path.join(commons.media_path, 'fortify', 'sde_fortify_map.xml')

class FortifyIntegrationError(IntegrationError):
    pass

class FortifyIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        config.add_custom_option("report_xml", "Fortify Report XML", "x", None)
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []

    def _make_raw_finding(self, node):
        """
        Extract finding information from an XML node.
        """
        entry = {}
        entry['cweid'] = node.getElementsByTagName("groupTitle")[0].firstChild.data
        entry['description'] = node.getElementsByTagName("groupTitle")[0].firstChild.data
        return entry

    def parse(self):
        try:
            base = minidom.parse(self.config['report_xml'])
        except KeyError, ke:
            raise FortifyIntegrationError("Missing configuration option 'report_xml'")
        except Exception, e:
            raise FortifyIntegrationError("Error opening report xml (%s)" % self.config['report_xml'])

        report_sections = base.getElementsByTagName('ReportSection')
        #for report_section in report_sections:
        #    if report_section.getElementsByTagName('Title')[0] == "Project Summary":
                
        self.report_id = "WebGoat"

        report_sections = base.getElementsByTagName('ReportSection')
        for report_section in report_sections:
            title = report_section.getElementsByTagName('Title')[0]
            if (title.firstChild.data == 'Issue Count by Category'):
                issue_listing = report_section.getElementsByTagName('IssueListing')[0]
                grouping_sections = issue_listing.getElementsByTagName('GroupingSection')
                for grouping_section in grouping_sections:
                    for i in range(0,int(grouping_section.attributes['count'].value)):
                        self.raw_findings.append( self._make_raw_finding(grouping_section) )

    def _make_finding(self, item):
        finding = {'cweid': item['cweid'], 'description': item['description']}
        if item.has_key('sourcefilepath'):
            finding['source'] = item['sourcefilepath']
        if item.has_key('line'):
            finding['line'] = item['line']
        if item.has_key('inputvector'):
            finding['source'] = item['inputvector']
        return finding

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
        
