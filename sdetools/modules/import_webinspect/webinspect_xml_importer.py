import os
import re
import xml.sax.handler
from sdetools.extlib.defusedxml import sax

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter

class WebInspectXMLContent(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.in_issue_node = False
        self.in_vuln_node = False
        self.in_issue_name_node = False
        self.in_session_node = False
        self.in_url_node = False
        self.raw_findings = []
        self.report_id = ""
        self.check_id = 0
        self.check_name_found = False

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'Issue':
            self.in_issue_node = True
        elif name == 'VulnerabilityID':
            self.in_vuln_node = True
        elif self.in_issue_node and not self.check_name_found and name == 'Name':
            self.in_issue_name_node = True
        elif name == 'Session':
            self.in_session_node = True
        elif self.in_session_node and name == 'Host':
            self.in_url_node = True

    def characters(self, data):
        if self.in_issue_node and self.in_vuln_node:
            self.check_id = data
        elif self.in_issue_node and self.in_issue_name_node:
            entry = {}
            entry['id'] = self.check_id
            entry['count'] = 1
            entry['type'] = 'check'
            entry['description'] = data
            self.raw_findings.append(entry)
            self.check_id = 0
            self.check_name_found = True
        elif self.in_session_node and self.in_url_node:
            self.report_id = data

    def endElement(self, name):
        if self.in_issue_node and name == 'Issue':
            self.in_issue_node = False
            self.check_name_found = False
        if self.in_issue_node and self.in_vuln_node and name == 'VulnerabilityID':
            self.in_vuln_node = False
        elif self.in_issue_node and self.in_issue_name_node and name == 'Name':
            self.in_issue_name_node = False
        elif self.in_session_node and name == 'Session':
            self.in_session_node = False
        elif self.in_session_node and self.in_url_node and name == 'Host':
            self.in_url_node = False
    
class WebInspectXMLImporter(BaseImporter):

    def __init__(self):
        super(WebInspectXMLImporter, self).__init__()

    def parse(self, xml_file):
        try:    
            self.parse_file(open(xml_file, 'rb'))
        except Exception, e:
            raise Exception("Error opening XML file (%s): %s" % (xml_file, e))

    def parse_file(self, xml_file):
        XMLReader = WebInspectXMLContent()
        try:    
            parser = sax.make_parser()
            parser.setContentHandler(XMLReader)
            parser.parse(xml_file)
        except Exception, e:
            raise Exception("Error opening XML file (%s): %s" % (xml_file, e))
        
        self.raw_findings = XMLReader.raw_findings
        self.report_id = XMLReader.report_id

    def parse_string(self, xml):
        XMLReader = WebInspectXMLContent()
        try:    
            sax.parseString(fvdl_xml, XMLReader)
        except Exception, e:
            raise e
        
        self.raw_findings = XMLReader.raw_findings
        self.report_id = XMLReader.report_id