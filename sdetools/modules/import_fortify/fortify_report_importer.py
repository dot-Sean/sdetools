import re

from sdetools.extlib.defusedxml import minidom
from sdetools.analysis_integration.base_integrator import BaseImporter
from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError


class FortifyReportImporter(BaseImporter):

    def __init__(self):
        super(FortifyReportImporter, self).__init__()

    def _make_raw_finding(self, node):
        group_title = node.getElementsByTagName("groupTitle")[0].firstChild.data
        weakness_count = int(node.attributes['count'].value)

        return {
            'id': group_title,
            'description': group_title,
            'count': weakness_count
        }

    def parse(self, report_xml):
        try:
            base = minidom.parse(report_xml)
        except Exception, e:
            raise FortifyIntegrationError("Error opening report xml %s Reason: %s" % report_xml, str(e))

        self.report_id = ""
        root = base.documentElement

        if root.tagName != "ReportDefinition":
            raise FortifyIntegrationError("Malformed report detected: ReportDefinition is not found")

        report_sections = root.getElementsByTagName('ReportSection')
        if not report_sections:
            raise FortifyIntegrationError("Malformed report detected: ReportSection not found")

        for report_section in report_sections:
            titles = report_section.getElementsByTagName('Title')
            if not titles:
                raise FortifyIntegrationError("Malformed report detected: Title not found")
            title = titles[0]
            if title.firstChild.data == 'Issue Count by Category':
                issue_listing = report_section.getElementsByTagName('IssueListing')[0]
                grouping_sections = issue_listing.getElementsByTagName('GroupingSection')
                for grouping_section in grouping_sections:
                    self.raw_findings.append(self._make_raw_finding(grouping_section))
            elif title.firstChild.data == 'Project Summary':
                subsection = report_section.getElementsByTagName('SubSection')[0]
                subsection_text = subsection.getElementsByTagName('Text')[0]
                m = re.search('Build Label:\s*(.+)', subsection_text.firstChild.data)
                if m:
                    self.report_id = m.group(1)
