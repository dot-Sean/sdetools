import os
from sdetools.extlib.defusedxml import minidom

from sdetools.sdelib.commons import media_path, UsageError
from sdetools.analysis_integration.base_integrator import BaseIntegrator, IntegrationError

__all__ = ['VeracodeIntegrator']

REQUIRED_ATTRIBS = ['issueid', 'cweid', 'categoryid', 'categoryname', 'description', 'severity', 'module','remediation_status']
LOCATION_ATTRIBS = ['sourcefilepath', 'sourcefile', 'line', 'location']

DEFAULT_MAPPING_FILE = os.path.join(media_path, 'veracode', 'sde_veracode_map.xml')

class VeracodeIntegrationError(IntegrationError):
    pass

class VeracodeIntegrator(BaseIntegrator):
    TOOL_NAME = "veracode"

    def __init__(self, config):
        supported_file_types = ['xml']
        super(VeracodeIntegrator, self).__init__(config, self.TOOL_NAME, supported_file_types, DEFAULT_MAPPING_FILE)

    def _make_raw_finding(self, node):
        """
        Extract finding information from an XML node.
        """
        entry = {}
        for attr in REQUIRED_ATTRIBS:
            if attr not in node.attributes.keys():
                raise VeracodeIntegrationError('Required attribute %s missing' % (attr))
            entry[attr] = node.attributes[attr].value
        for attr in LOCATION_ATTRIBS:
            if attr in node.attributes.keys():
                entry[attr] = node.attributes[attr].value
        return entry

    def parse_report_file(self, report_file, report_type):
        if report_type != 'xml':
            raise UsageError("Unsupported file type (%s)" % report_type)

        try:
            base = minidom.parse(report_file)
        except Exception, e:
            raise VeracodeIntegrationError("Error opening report xml (%s)" % report_file)

        detailed_reports = base.getElementsByTagName('detailedreport')

        if len(detailed_reports) != 1:
            raise VeracodeIntegrationError('An unexpected number of detailedreport nodes found (%d)' %
                                           len(detailed_reports))
        dr = detailed_reports[0]
        report_id = "%s (%s-b%s)" % (
            dr.attributes['app_name'].value,
            dr.attributes['app_id'].value,
            dr.attributes['build_id'].value
        )
        findings = [self._make_raw_finding(node) for node in base.getElementsByTagName('flaw')]

        # Veracode tracks 'fixed' flaws - prune them out
        for flaw in list(findings):
            if flaw['remediation_status'] == 'Fixed':
                findings.remove(flaw)

        return findings, report_id

    def _make_finding(self, item):
        finding = {'weakness_id': item['cweid'], 'description': item['categoryname']}
        if item.has_key('sourcefilepath'):
            finding['source'] = item['sourcefilepath']
        if item.has_key('line'):
            finding['line'] = item['line']
        if item.has_key('inputvector'):
            finding['source'] = item['inputvector']
        return finding

    def generate_findings(self):
        return [self._make_finding(item) for item in self.findings]

