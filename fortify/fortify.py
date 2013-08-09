#!/usr/bin/python
import sys
import logging
import suds

#logging.basicConfig(level=logging.INFO)
#logging.getLogger('suds.client').setLevel(logging.DEBUG)
#logging.getLogger('suds.transport').setLevel(logging.DEBUG)
#logging.getLogger('suds.transport.http').setLevel(logging.DEBUG)

security = suds.wsse.Security()
token = suds.wsse.UsernameToken(sys.argv[1], sys.argv[2])
security.tokens.append(token)

client = suds.client.Client("http://127.0.0.1:8181/ssc/fm-ws/services/fws.wsdl", 
    autoblend=True,
    location="http://127.0.0.1:8181/ssc/fm-ws/services/",
    wsse=security)
ret = client.service.CreateAuditSession()
if ('code' not in ret) or (ret['code'] != 0):
    raise Exception('Error!')
#ret = client.service.ProjectList()
#if ('code' not in ret) or (ret['code'] != 0):
#    raise Exception('Error!')
#project_list = ret
ret = client.service.ActiveProjectVersionList()
if ('code' not in ret) or (ret['code'] != 0):
    raise Exception('Error!')
active_project_version_list = ret['ProjectVersion']
client.service.GetSingleUseFPRDownloadToken()
ret = client.last_received()
token = ret.getChild('Envelope').getChild('Body').getChild('GetAuthenticationTokenResponse').getChild('token').text
print active_project_version_list
print 'Token: %s' % token
