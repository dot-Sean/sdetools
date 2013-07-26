import os
import re
from xml.sax.handler import ContentHandler
from sdetools.extlib.defusedxml import sax

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter

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

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'IssueType':
            # <IssueType ID="attCrossSiteScripting" Count="10">
            self.in_issuetype_node = True
            self.count = int(attrs['Count'])
            # collect Count attribute value
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
            entry['id'] = data
            entry['count'] = self.count
            entry['description'] = data
            self.raw_findings.append(entry)
            
            # reset count
            self.count = 0

    def endElement(self, name):
        if self.in_issuetype_node and name == 'IssueType':
            self.in_issuetype_node = False
        if self.in_issuetype_advisory_node and name == 'advisory':
            self.in_issuetype_advisory_node = False
        if self.in_issuetype_advisory_threatclass_node and name == 'threatClassification':
            self.in_issuetype_advisory_threatclass_node = False
        elif self.in_issuetype_advisory_threatclass_node and name == 'name':
            self.in_issuetype_advisory_threatclass_name_node = False
        elif self.in_hosts_host_id_node and name == 'Host':
            self.in_hosts_host_id_node = False
        elif self.in_hosts_node and name == 'Hosts':
            self.in_hosts_node = False
    
# TODO: Use defusedxml interface
class AppScanXMLImporter(BaseImporter):

    def __init__(self):
        super(AppScanXMLImporter, self).__init__()

    def parse(self, xml_file):
        try:    
            self.parse_file(open(xml_file, 'rb'))
        except Exception, e:
            raise Exception("Error opening AppScan XML file (%s): %s" % (xml_file, e))

    def parse_file(self, xml_file):
        AppScanReader = AppScanXMLContent()
        try:    
            parser = sax.make_parser()
            parser.setContentHandler(AppScanReader)
            parser.parse(xml_file)
        except Exception, e:
            raise Exception("Error opening AppScan XML file (%s): %s" % (xml_file, e))
        
        self.raw_findings = AppScanReader.raw_findings
        self.report_id = AppScanReader.report_id

    def parse_string(self, appscan_xml):
        AppScanReader = AppScanXMLContent()
        try:    
            xml.sax.parseString(appscan_xml, AppScanReader)
        except Exception, e:
            raise e
        
        self.raw_findings = AppScanReader.raw_findings
        self.report_id = AppScanReader.report_id
    
