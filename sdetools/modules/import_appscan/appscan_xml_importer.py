from xml.sax.handler import ContentHandler

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseXMLImporter

class AppScanXMLContent(ContentHandler):
    def __init__(self):
        self.in_hosts_node = False
        self.in_hosts_host_id_node = False
        self.in_issuetype_node = False
        self.in_issuetype_advisory_node = False
        self.in_issuetype_advisory_threatclass_node = False
        self.in_issuetype_advisory_threatclass_name_node = False
        self.raw_findings = []
        self.count = 0
        self.report_id = ""
        self.check_id = ""

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'IssueType':
            self.in_issuetype_node = True
            self.count = int(attrs['Count'])
            self.check_id = attrs['ID']
        elif self.in_issuetype_node and name == 'advisory':
            self.in_issuetype_advisory_node = True
        elif self.in_issuetype_advisory_node and name == 'threatClassification':
            self.in_issuetype_advisory_threatclass_node = True
        elif self.in_issuetype_advisory_threatclass_node and name == 'name':
            self.in_issuetype_advisory_threatclass_name_node = True
        elif name == 'Hosts':
            self.in_hosts_node = True
        elif self.in_hosts_node and name == 'Host':
            self.in_hosts_host_id_node = True
            self.report_id = attrs['Name']

    def characters(self, data):
        if self.in_issuetype_advisory_threatclass_name_node:
            entry = {}
            entry['id'] = self.check_id
            entry['count'] = self.count
            entry['description'] = data

            self.raw_findings.append(entry)
            
            # reset
            self.count = 0
            self.check_id = ""

    def endElement(self, name):
        if self.in_issuetype_node and name == 'IssueType':
            self.in_issuetype_node = False
        elif self.in_issuetype_advisory_node and name == 'advisory':
            self.in_issuetype_advisory_node = False
        elif self.in_issuetype_advisory_threatclass_node and name == 'threatClassification':
            self.in_issuetype_advisory_threatclass_node = False
        elif self.in_issuetype_advisory_threatclass_node and name == 'name':
            self.in_issuetype_advisory_threatclass_name_node = False
        elif self.in_hosts_host_id_node and name == 'Host':
            self.in_hosts_host_id_node = False
        elif self.in_hosts_node and name == 'Hosts':
            self.in_hosts_node = False
    
class AppScanXMLImporter(BaseXMLImporter):

    def __init__(self):
        super(AppScanXMLImporter, self).__init__()

    def _get_content_handler(self):
        return AppScanXMLContent()
    
