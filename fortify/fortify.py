#!/usr/bin/python
import sys
import logging
import suds

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)
logging.getLogger('suds.transport').setLevel(logging.DEBUG)
logging.getLogger('suds.transport.http').setLevel(logging.DEBUG)

security = suds.wsse.Security()
token = suds.wsse.UsernameToken(sys.argv[1], sys.argv[2])
security.tokens.append(token)

client = suds.client.Client("http://127.0.0.1:8180/ssc/fm-ws/services/fws.wsdl", 
    autoblend=True,
    location="http://127.0.0.1:8180/ssc/fm-ws/services/",
    wsse=security)
client.service.GetSingleUseFPRDownloadToken()
print client.last_received()