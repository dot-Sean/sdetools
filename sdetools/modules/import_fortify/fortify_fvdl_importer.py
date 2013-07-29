import os
import xml.sax.handler

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseXMLImporter

class FVDLXMLContent(xml.sax.handler.ContentHandler):

    def __init__(self):
        self.in_build_node = False
        self.in_build_build_id_node = False
        self.in_vuln_node = False
        self.in_vuln_class_info_node = False
        self.in_vuln_class_info_type_node = False
        self.raw_findings = []
        self.report_id = ""

    def processingInstruction(self, target, data):
        pass

    def startElement(self, name, attrs):
        if name == 'Vulnerability':
            self.in_vuln_node = True
        elif self.in_vuln_node and name == 'ClassInfo':
            self.in_vuln_class_info_node = True
        elif self.in_vuln_class_info_node and name == 'Type':
            self.in_vuln_class_info_type_node = True
        elif name == 'Build':
            self.in_build_node = True
        elif self.in_build_node and name == 'BuildID':
            self.in_build_build_id_node = True

    def characters(self, data):
        if self.in_vuln_class_info_type_node:
            entry = {}
            entry['id'] = data
            entry['count'] = 1
            entry['description'] = data
            self.raw_findings.append(entry)
        elif self.in_build_build_id_node:
            self.report_id = data

    def endElement(self, name):
        if self.in_vuln_node and name == 'Vulnerability':
            self.in_vuln_node = False
        if self.in_vuln_class_info_node and name == 'ClassInfo':
            self.in_vuln_class_info_node = False
        if self.in_vuln_class_info_type_node and name == 'Type':
            self.in_vuln_class_info_type_node = False
        elif self.in_build_build_id_node and name == 'BuildID':
            self.in_build_build_id_node = False
        elif self.in_build_node and name == 'Build':
            self.in_build_node = False
    
class FortifyFVDLImporter(BaseXMLImporter):

    def __init__(self):
        super(FortifyFVDLImporter, self).__init__()

    def _get_content_handler(self):
        return FVDLXMLContent()