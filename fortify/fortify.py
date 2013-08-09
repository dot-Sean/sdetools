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
<<<<<<< HEAD
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
=======
import pdb; pdb.set_trace()

spec = []
for method in client.wsdl.services[0].ports[0].methods.values(): 
    if not method.soap.input.body.parts:
        args = ''
    else:
        args = str(client.factory.create(method.soap.input.body.parts[0].element[0]))
    spec.append((method.name, args))
spec.sort()
for item in spec:
    print item[0]
    print '\n    '.join(item[1].split('\n'))
    print
>>>>>>> 49f0f77238e08f0ce7460037615b5b1ff029580f
