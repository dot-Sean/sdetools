import httplib
import re
import os
import socket
import urllib2
import base64

try:
    import ssl
    ssl_lib_found = True
except ImportError:
    ssl_lib_found = False

import logging

from sdetools.sdelib import commons

ssl_warned = False

CERT_PATH_NAME = os.path.join(commons.media_path, 'ssl')
CA_CERTS_FILE = os.path.join(CERT_PATH_NAME, 'ca_bundle.crt')

try:
    open(CA_CERTS_FILE).close()
except:
    logging.warning('Unable to access SSL root certificate: %s' % (CA_CERTS_FILE))

class InvalidCertificateException(httplib.HTTPException, urllib2.URLError):
    def __init__(self, host, cert, reason):
        httplib.HTTPException.__init__(self)
        self.host = host
        self.cert = cert
        self.reason = reason

    def __str__(self):
        return ('Host %s returned an invalid certificate (%s) %s\n' %
                (self.host, self.reason, self.cert))

class CertValidatingHTTPSConnection(httplib.HTTPConnection):
    default_port = httplib.HTTPS_PORT

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                             ca_certs=None, strict=None, sde_proxy_auth='', **kwargs):
        httplib.HTTPConnection.__init__(self, host, port, strict, **kwargs)
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_certs = ca_certs
        if self.ca_certs:
            self.cert_reqs = ssl.CERT_REQUIRED
        else:
            self.cert_reqs = ssl.CERT_NONE
        self.sde_proxy_auth = sde_proxy_auth

    def _GetValidHostsForCert(self, cert):
        if 'subjectAltName' in cert:
            return [x[1] for x in cert['subjectAltName']
                         if x[0].lower() == 'dns']
        else:
            return [x[0][1] for x in cert['subject']
                            if x[0][0].lower() == 'commonname']

    def _ValidateCertificateHostname(self, cert, hostname):
        hosts = self._GetValidHostsForCert(cert)
        for host in hosts:
            host_re = host.replace('.', '\.').replace('*', '[^.]*')
            if re.search('^%s$' % (host_re,), hostname, re.I):
                return True
        return False

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            if ('Proxy-Authorization' not in self._tunnel_headers) and (self.sde_proxy_auth):
                proxy_auth = base64.b64encode(self.sde_proxy_auth).strip()
                self._tunnel_headers['Proxy-Authorization'] = 'Basic %s' % proxy_auth
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(sock, keyfile=self.key_file,
                                          certfile=self.cert_file,
                                          cert_reqs=self.cert_reqs,
                                          ca_certs=self.ca_certs)
        if self.cert_reqs & ssl.CERT_REQUIRED:
            cert = self.sock.getpeercert()
            hostname = self.host.split(':', 0)[0]
            if not self._ValidateCertificateHostname(cert, hostname):
                raise InvalidCertificateException(hostname, cert,
                                                  'hostname mismatch')


class VerifiedHTTPHandler(urllib2.HTTPHandler):
    def __init__(self, debuglevel, **kwargs):
        urllib2.AbstractHTTPHandler.__init__(self, debuglevel)
        self._connection_args = kwargs

    def http_open(self, req):
        if req.has_proxy():
            sde_proxy_auth = self._connection_args['sde_proxy_auth']
            if ('Proxy-Authorization' not in req.headers) and (sde_proxy_auth):
                proxy_auth_val = base64.b64encode(sde_proxy_auth).strip()
                req.headers['Proxy-Authorization'] = 'Basic %s' % proxy_auth_val
        return self.do_open(httplib.HTTPConnection, req)

    http_request = urllib2.HTTPHandler.do_request_

class VerifiedHTTPSHandler(urllib2.HTTPSHandler):
    def __init__(self, debuglevel, **kwargs):
        urllib2.AbstractHTTPHandler.__init__(self, debuglevel)
        self._connection_args = kwargs

    def https_open(self, req):
        def https_class_wrapper(host, **kwargs):
            full_kwargs = dict(self._connection_args)
            full_kwargs.update(kwargs)
            return CertValidatingHTTPSConnection(host, **full_kwargs)

        try:
            return self.do_open(https_class_wrapper, req)
        except urllib2.URLError, e:
            if type(e.reason) == ssl.SSLError and e.reason.args[0] == 1:
                raise InvalidCertificateException(req.host, '',
                                                  e.reason.args[1])
            raise

    https_request = urllib2.HTTPSHandler.do_request_

def get_http_handler(mode, debuglevel, sde_proxy_auth=''):
    global ssl_warned

    if mode == 'http':
        return VerifiedHTTPHandler(debuglevel=debuglevel, sde_proxy_auth=sde_proxy_auth)
    elif mode == 'https':
        if not ssl_lib_found:
            if not ssl_warned:
                logging.warning('Missing ssl library for python: SSL certificates can'
                    ' NOT be validated\n (use python 2.6 or install ssl for python)')
                ssl_warned = True
            return urllib2.HTTPSHandler(debuglevel=debuglevel)
        else:
            return VerifiedHTTPSHandler(debuglevel=debuglevel, 
                    sde_proxy_auth=sde_proxy_auth, ca_certs=CA_CERTS_FILE)
    raise KeyError, mode
    
