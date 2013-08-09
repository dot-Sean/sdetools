import os
import datetime
import urllib2
import httplib

from sdetools.extlib.defusedxml import minidom
from sdetools.extlib import http_req

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseIntegrator

from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError
from sdetools.modules.import_fortify.fortify_report_importer import FortifyReportImporter
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter
from sdetools.modules.import_fortify.fortify_fvdl_importer import FortifyFVDLImporter

__all__ = ['FortifyIntegrator']

DEFAULT_MAPPING_FILE = os.path.join(commons.media_path, 'fortify', 'sde_fortify_map.xml')


class FortifyIntegrator(BaseIntegrator):
    TOOL_NAME = "fortify"

    def __init__(self, config):
        config.add_custom_option("report_xml", "Fortify Report XML", "x", None)
        config.add_custom_option('alm_method','ss', default='')
        config.add_custom_option('alm_server','sx', default='')
        config.add_custom_option('alm_user','sy',default='')
        config.add_custom_option('alm_pass','sz',default='')
        
        super(FortifyIntegrator, self).__init__(config, DEFAULT_MAPPING_FILE)
        self.raw_findings = []
        self.importer = None

    def consume(self):
        
        if __name__ in self.config['debug_mods']:
            config.debug = 1
        
        opener = http_req.get_opener(self.config['alm_method'], self.config['alm_server'])
        self.config['alm_server'] = opener.server

        created = datetime.datetime.utcnow()
        expires = created + datetime.timedelta(minutes=5)

        login_soap = """<?xml version='1.0' encoding='UTF-8'?>
   <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
      <soapenv:Header>
         <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" soapenv:mustUnderstand="1">
            <wsu:Timestamp xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" wsu:Id="Timestamp-2">
               <wsu:Created>%s</wsu:Created>
               <wsu:Expires>%s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:UsernameToken xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" wsu:Id="UsernameToken-1">
               <wsse:Username>%s</wsse:Username>
               <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">%s</wsse:Password>
            </wsse:UsernameToken>
         </wsse:Security>
      </soapenv:Header>
      <soapenv:Body>
         <GetSingleUseFPRDownloadTokenRequest xmlns="http://www.fortify.com/schema/fws" xmlns:ns2="xmlns://www.fortifysoftware.com/schema/wsTypes" xmlns:ns4="xmlns://www.fortifysoftware.com/schema/activitytemplate" xmlns:ns3="xmlns://www.fortifysoftware.com/schema/seed" xmlns:ns5="xmlns://www.fortify.com/schema/issuemanagement" xmlns:ns6="xmlns://www.fortify.com/schema/audit" xmlns:ns7="xmlns://www.fortifysoftware.com/schema/runtime" xmlns:ns8="xmlns://www.fortify.com/schema/attachments" />
      </soapenv:Body>
   </soapenv:Envelope>""" % (created.isoformat('T')[:-3], expires.isoformat('T')[:-3], self.config['alm_user'],self.config['alm_pass'])
        
        # Attempt to login
        print '%s://%s/ssc/fm-ws/services' % (self.config['alm_method'], self.config['alm_server'])
        
        req = urllib2.Request('%s://%s/ssc/fm-ws/services' %
                (self.config['alm_method'], self.config['alm_server']), data=login_soap, 
                headers={'Content-Type': 'text/xml'})
        
        stream = opener.open(req)
        
        try:
            base = minidom.parse(stream)
        except Exception, e:
            raise FortifyIntegrationError("Error opening Fortify SSC response xml (%s)" % e)
        
        print base
        token = base.getElementsByTagName('ns2:token')[0].firstChild.nodeValue
        print token
        
        req = urllib2.Request('%s://%s/ssc/download/currentStateFprDownload.html?id=4&mat=%s&clientVersion=3.60.0065' %
                (self.config['alm_method'], self.config['alm_server'], token), data='', 
                headers={'Content-Type': 'text/xml'})

        stream = opener.open(req)
        print stream
        with open('C:/Users/Geoffrey/Downloads/test.fpr', 'wb') as fp:
          while True:
            try:
                chunk = stream.read()
            except httplib.IncompleteRead as e:
                chunk = e.partial
            if not chunk: break
            fp.write(chunk)

        self.config['report_xml'] = 'C:/Users/Geoffrey/Downloads/test.fpr'
        self.parse()

    def parse(self):

        try:
            fileName, file_extension = os.path.splitext(self.config['report_xml'])
        except KeyError, ke:
            raise FortifyIntegrationError("Missing configuration option 'report_xml'")

        if file_extension == '.xml':
            self.importer = FortifyReportImporter()
        elif file_extension == '.fpr':
            self.importer = FortifyFPRImporter()
        elif file_extension == '.fvdl':
            self.importer = FortifyFVDLImporter()
        else:
            raise FortifyIntegrationError("Unsupported file type (%s)" % file_extension)

        self.importer.parse(self.config['report_xml'])
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id

        if not self.report_id:
            raise FortifyIntegrationError("Report ID not found in report file (%s)" % self.config['report_xml'])

    def _make_finding(self, item):
        return {'weakness_id': item['id'], 'description': item['description'], 'count': item['count']}

    def generate_findings(self):
        return [self._make_finding(item) for item in self.raw_findings]
