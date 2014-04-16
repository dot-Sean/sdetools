import sys
import suds
import os
import re
import urllib2
import httplib
import logging
import tempfile
import xml.parsers.expat
import socket
from suds.plugin import MessagePlugin
from suds.transport.https import HttpAuthenticated

logging.getLogger('suds').setLevel(logging.WARNING)

from sdetools.extlib import http_req
from sdetools.sdelib import commons
from sdetools.analysis_integration.base_integrator import BaseImporter
from sdetools.modules.import_fortify.fortify_integration_error import FortifyIntegrationError
from sdetools.modules.import_fortify.fortify_fpr_importer import FortifyFPRImporter
from sdetools.sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class TokenPlugin(MessagePlugin):

    def __init__(self, token_value):
        self.auth_token=token_value

    def marshalled(self, context):
        header = context.envelope.getChild('Header')
        header.set('xmlns:axis2ns1', 'www.fortify.com/schema')
        header.set('axis2ns1:token', self.auth_token)

class FortifySSCImporter(BaseImporter):

    def __init__(self, config):
        super(FortifySSCImporter, self).__init__()
        self.config = config
        self.soap_endpoint = "%s://%s/ssc/fm-ws/services" %  (self.config['ssc_method'], self.config['ssc_server'])

    def _get_ssc_client(self):

        security = suds.wsse.Security()
        
        suds_plugins = []

        if self.config['ssc_authtoken']:
            token = suds.wsse.UsernameToken('', '')
            suds_plugins.append(TokenPlugin(self.config['ssc_authtoken']))
        else:
            token = suds.wsse.UsernameToken(self.config['ssc_user'], self.config['ssc_pass'])
        security.tokens.append(token)
        
        try:
            client = suds.client.Client("%s/fws.wsdl" % self.soap_endpoint, 
                autoblend=True,
                location=self.soap_endpoint,
                wsse=security,
                plugins=suds_plugins,
                transport=HttpAuthenticated())
        except (xml.parsers.expat.ExpatError, socket.error, urllib2.URLError), err:
            raise FortifyIntegrationError('Error talking to Fortify SSC service. Please check server URL. Reason: %s' % err)

        return client

    def _get_project_version_id(self, client, project_name, project_version):
    
        logger.info('Retrieving project list')

        try:
            ret = client.service.ProjectList()
        except (xml.parsers.expat.ExpatError, socket.error, urllib2.URLError, suds.WebFault), err:
            raise FortifyIntegrationError('Unable to retrieve project list. Reason: %s' % err)
        
        if 'code' not in ret:
            raise FortifyIntegrationError('Unable to retrieve project list')
        elif ret['code'] != 0:
            raise FortifyIntegrationError('Unable to retrieve project list. Reason: %s (%d)' % 
                                          ret['msg'], ret['code'])

        project_version_id = None
        proj_id = None

        project_list = ret['Project']
        for proj in project_list:
            if proj['Name'] == project_name:
                proj_id = proj['Id']
                break

        if not proj_id:
            raise FortifyIntegrationError("Project %s not found in SSC" % project_name)

        logger.info('Retrieving active project version list')

        try:
            ret = client.service.ActiveProjectVersionList()
        except (xml.parsers.expat.ExpatError, socket.error, urllib2.URLError, suds.WebFault), err:
            raise FortifyIntegrationError('Unable to retrieve project versions. Reason: %s' % err)
        
        if 'code' not in ret:
            raise FortifyIntegrationError('Unable to retrieve project versions')
        elif ret['code'] != 0:
            raise FortifyIntegrationError('Unable to retrieve project versions. Reason: %s (%d)' % 
                                          ret['msg'], ret['code'])

        active_project_version_list = ret['ProjectVersion']
        for proj in active_project_version_list:
            if proj['ProjectId'] == proj_id and proj['Name'] == project_version:
                project_version_id = proj['Id']
                break
            
        return project_version_id
    
    def _download_file(self, stream, fprfd):

        logger.info('Downloading FPR file')

        fp = os.fdopen(fprfd, 'wb')
        while True:
            try:
                chunk = stream.read()
            except httplib.IncompleteRead as e:
                chunk = e.partial
            if not chunk: break
            fp.write(chunk)
        fp.close()
    
    def run(self):

        logger.info('Initiating connection to Fortify SSC service')    
        client = self._get_ssc_client()

        project_version_id = self._get_project_version_id(client, self.config['ssc_project_name'], 
                                             self.config['ssc_project_version'])
        if not project_version_id:
            raise FortifyIntegrationError("Version %s of project %s not found in SSC" % 
                         (self.config['ssc_project_version'], self.config['ssc_project_name']))

        if self.config['ssc_test_connection']:
            return
        
        logger.info('Initiating FPR download request for project %s version %s' %
                    (self.config['ssc_project_name'], self.config['ssc_project_version']))

        try:
            client.service.GetSingleUseFPRDownloadToken()
        except (xml.parsers.expat.ExpatError, socket.error, urllib2.URLError, suds.WebFault), err:
            raise FortifyIntegrationError('Could not initiate FPR download: %s' % err) 
            
        ret = client.last_received()
        token = ret.getChild('Envelope').getChild('Body').getChild('GetAuthenticationTokenResponse').getChild('token').text

        req = urllib2.Request('%s://%s/ssc/download/currentStateFprDownload.html?id=%s&mat=%s&clientVersion=3.60.0065' %
                (self.config['ssc_method'], self.config['ssc_server'], project_version_id, token))

        opener = http_req.get_opener(self.config['ssc_method'], self.config['ssc_server'])
        stream = opener.open(req)

        # Download the FPR file to a temporary file
        temp_fd, fpr_fname = tempfile.mkstemp()

        try:
            self._download_file(stream, temp_fd)
        except Exception, e:
            os.remove(fpr_fname)
            raise FortifyIntegrationError("Could not download FPR file: %s" % e)

        logger.info('FPR file downloaded successfully')
            
        self.importer = FortifyFPRImporter()
        
        try:
            self.importer.parse(fpr_fname)
        finally:
            os.remove(fpr_fname)

        self.raw_findings = self.importer.raw_findings
        self.report_id = self.importer.report_id
