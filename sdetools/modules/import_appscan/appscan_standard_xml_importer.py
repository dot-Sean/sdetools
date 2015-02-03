from sdetools.analysis_integration.base_integrator import BaseXMLImporter, BaseContentHandler


class AppScanStandardXMLContent(BaseContentHandler):
    def __init__(self):
        self.saw_xml_report_node = False # top-level node
        self.saw_app_scan_node = False
        self.in_hosts_node = False
        self.in_hosts_host_id_node = False
        self.in_issuetype_node = False
        self.in_issuetype_advisory_node = False
        self.in_issuetype_advisory_threatclass_node = False
        self.in_issuetype_advisory_threatclass_name_node = False
        self.findings = []
        self.count = 0
        self.id = ""
        self.check_id = ""

    def valid_content_detected(self):
        return self.saw_app_scan_node

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'XmlReport':
            self.saw_xml_report_node = True
        elif self.saw_xml_report_node and name == 'AppScanInfo':
            self.saw_app_scan_node = True
        elif name == 'IssueType':
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
            self.id = attrs['Name']

    def characters(self, data):
        if self.in_issuetype_advisory_threatclass_name_node:
            entry = {}
            entry['id'] = self.check_id
            entry['count'] = self.count
            entry['description'] = data

            self.findings.append(entry)
            
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


class AppScanStandardXMLImporter(BaseXMLImporter):

    def __init__(self):
        super(AppScanStandardXMLImporter, self).__init__()
        self.edition = 'standard'

    def _get_content_handler(self):
        return AppScanStandardXMLContent()

    def get_edition(self):
        return self.edition