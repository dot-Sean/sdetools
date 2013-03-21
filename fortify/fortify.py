#!/usr/bin/python
import logging
import suds

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)
logging.getLogger('suds.transport').setLevel(logging.DEBUG)
logging.getLogger('suds.transport.http').setLevel(logging.DEBUG)

client = suds.client.Client("http://127.0.0.1:8180/ssc/fm-ws/services/fws.wsdl", autoblend=True)
import pdb
pdb.set_trace()
client.service.CreateAuditSession()

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
