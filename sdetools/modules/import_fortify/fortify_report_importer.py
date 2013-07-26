import os
import re
from xml.dom import minidom

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter

class FortifyReportImporter(BaseImporter):

    def __init__(self):
        super(FortifyReportImporter, self).__init__()

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

    def parse(self, report_xml):
        try:
            base = minidom.parse(report_xml)
        except Exception, e:
            raise FortifyIntegrationError("Error opening report xml (%s)" % report_xml)
              
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