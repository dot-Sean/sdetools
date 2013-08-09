import sys
import suds
import os
import re
import urllib2
import httplib
import logging
import tempfile

from sdetools.extlib.defusedxml import minidom
from sdetools.extlib import http_req

from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter
from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter


class FortifySSCImporter(BaseImporter):

    def __init__(self, config):
        super(FortifySSCImporter, self).__init__()
        self.config = config

    def run(self):

        logging.getLogger('suds').setLevel(logging.WARNING)

        security = suds.wsse.Security()
        token = suds.wsse.UsernameToken(self.config['ssc_user'], self.config['ssc_pass'])
        security.tokens.append(token)
        
        soap_endpoint = "%s://%s/ssc/fm-ws/services/fws.wsdl" %  (self.config['ssc_method'], self.config['ssc_server'])
       
        client = suds.client.Client("%s/fws.wsdl" % soap_endpoint, 
            autoblend=True,
            location=soap_endpoint,
            wsse=security)

        ret = client.service.CreateAuditSession()
        if ('code' not in ret) or (ret['code'] != 0):
            raise Exception('Error!')

        ret = client.service.ProjectList()
        if ('code' not in ret) or (ret['code'] != 0):
            raise Exception('Error!')

        # Derive the projectVersionId
        project_version_id = None
        proj_id = None

        project_list = ret['Project']
        for proj in project_list:
            if proj['Name'] == self.config['ssc_project_name']:
                proj_id = proj['Id']
                break

        if not proj_id:
            raise FortifyIntegrationError("Project %s not found in SSC" % self.config['ssc_project_name'])

        ret = client.service.ActiveProjectVersionList()
        if ('code' not in ret) or (ret['code'] != 0):
            raise Exception('Error!')

        active_project_version_list = ret['ProjectVersion']
        for proj in active_project_version_list:
            if proj['ProjectId'] == proj_id and proj['Name'] == self.config['ssc_project_version']:
                project_version_id = proj['Id']
                break
            
        if not project_version_id:
            raise FortifyIntegrationError("Version %s of project %s not found in SSC" % self.config['ssc_project_version'], self.config['ssc_project_name'])

        client.service.GetSingleUseFPRDownloadToken()
        ret = client.last_received()
        token = ret.getChild('Envelope').getChild('Body').getChild('GetAuthenticationTokenResponse').getChild('token').text

        req = urllib2.Request('%s://%s/ssc/download/currentStateFprDownload.html?id=%s&mat=%s&clientVersion=3.60.0065' %
                (self.config['ssc_method'], self.config['ssc_server'], project_version_id, token), data='', 
                headers={'Content-Type': 'text/xml'})

        opener = http_req.get_opener(self.config['ssc_method'], self.config['ssc_server'])

        stream = opener.open(req)

        fprfd, fpr_fname = tempfile.mkstemp()
        fp = open(fpr_fname, 'wb')
        while True:
            try:
                chunk = stream.read()
            except httplib.IncompleteRead as e:
                chunk = e.partial
            if not chunk: break
            fp.write(chunk)
        fp.close()
        
        self.importer = FortifyFPRImporter()
        self.importer.parse(fpr_fname)
        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id
        
        # clean up temporary file
        #os.remove(fpr_fname)
        
