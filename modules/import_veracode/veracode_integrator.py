import os
from xml.dom import minidom

from base_integrator import BaseIntegrator, IntegrationError

REQUIRED_ATTRIBS = ['issueid', 'cweid', 'categoryid', 'categoryname', 'description', 'severity', 'module']
LOCATION_ATTRIBS = ['sourcefilepath', 'sourcefile', 'line', 'location']
SOURCE_NAME = "Veracode"

__all__ = ['VeracodeIntegrator']

DEFAULT_MAPPING_FILE = os.path.join('docs', 'veracode', 'sde_veracode_map.xml')

class VeracodeIntegrationError(IntegrationError):
    pass

class VeracodeIntegrator(BaseIntegrator):

    def __init__(self, config):
        config.add_custom_option("report_xml", "Veracode Report XML", "x", None)
        super(VeracodeIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []

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

    def get_tool_name(self):
        return SOURCE_NAME

    def parse(self):
        try:
            base = minidom.parse(self.config['report_xml'])
        except KeyError, ke:
            raise VeracodeIntegrationError("Missing configuration option 'report_xml'")
        except Exception, e:
            raise VeracodeIntegrationError("Error opening report xml (%s)" % self.config['report_xml'])

        detailed_reports = base.getElementsByTagName('detailedreport')
        if len(detailed_reports) != 1:
            raise VeracodeIntegrationError('An unexpected number of detailedreport nodes found (%d)' % len(detailed_reports))
        dr = detailed_reports[0]
        self.report_id = "%s (%s-b%s)" % (
                dr.attributes['app_name'].value,
                dr.attributes['app_id'].value,
                dr.attributes['build_id'].value )

        self.raw_findings[:] = [self._make_raw_finding(node)
                                for node in base.getElementsByTagName('flaw')]

    def output_raw_findings(self):
        for item in self.raw_findings:
            print '%5s,%5s,%5s' % (item['issueid'], item['cweid'], item['categoryid'])
            print item['description'][:120]

    def get_raw_findings(self):
        return self.raw_findings

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
        return [self._make_finding(item) for item in self.get_raw_findings()]
