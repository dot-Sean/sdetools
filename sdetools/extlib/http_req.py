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

class ExtendedMethodRequest(urllib2.Request):
    GET = 'GET'
    HEAD = 'HEAD'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'

    def __init__(self, url, data=None, headers={},
                 origin_req_host=None, unverifiable=False, method=None):
        urllib2.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)
        self.method = method

    def get_method(self):
        if self.method:
            return self.method

        return urllib2.Request.get_method(self)

class ExtendedMethodHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Return a Request or None in response to a redirect.

        This is called by the http_error_30x methods when a
        redirection response is received.  If a redirection should
        take place, return a new Request to allow http_error_30x to
        perform the redirect.  Otherwise, raise HTTPError if no-one
        else should try to handle this url.  Return None if you can't
        but another Handler might.
        """
        m = req.get_method()
        if (code in (301, 302, 303, 307) and m in ("GET", "HEAD")
            or code in (301, 302, 303) and m in ("POST", "PUT", "DELETE")):
            # Strictly (according to RFC 2616), 301 or 302 in response
            # to a POST MUST NOT cause a redirection without confirmation
            # from the user (of urllib2, in this case).  In practice,
            # essentially all clients do redirect in this case, so we
            # do the same.
            # be conciliant with URIs containing a space
            newurl = newurl.replace(' ', '%20')
            return ExtendedMethodRequest(newurl,
                           data=req.get_data(),
                           headers=req.headers,
                           origin_req_host=req.get_origin_req_host(),
                           unverifiable=True, 
                           method=req.get_method())
        else:
            raise HTTPError(req.get_full_url(), code, msg, headers, fp)

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
                             ca_certs=None, strict=None, **kwargs):
        httplib.HTTPConnection.__init__(self, host, port, strict, **kwargs)
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_certs = ca_certs
        if self.ca_certs:
            self.cert_reqs = ssl.CERT_REQUIRED
        else:
            self.cert_reqs = ssl.CERT_NONE

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
            if type(e.reason) is ssl.SSLError:
                raise InvalidCertificateException(req.host, '',
                                                  e.reason.args[1])
            raise

    https_request = urllib2.HTTPSHandler.do_request_

def get_http_handler(mode, debuglevel=0):
    global ssl_warned

    if mode == 'http':
        return urllib2.HTTPHandler(debuglevel=debuglevel)
    elif mode == 'https':
        if not ssl_lib_found:
            if not ssl_warned:
                logging.warning('Missing ssl library for python: SSL certificates can'
                    ' NOT be validated\n (use python 2.6 or install ssl for python)')
                ssl_warned = True
            return urllib2.HTTPSHandler(debuglevel=debuglevel)
        else:
            return VerifiedHTTPSHandler(debuglevel=debuglevel, ca_certs=CA_CERTS_FILE)
    raise KeyError, mode

def get_opener(method, server, proxy=None, debuglevel=0):
    handler = [get_http_handler(method, debuglevel)]
    if '|' in server:
        server, http_proxy = server.split('|', 1)
        handler.append(urllib2.ProxyHandler({method: http_proxy}))
    handler.append(ExtendedMethodHTTPRedirectHandler)
    opener = urllib2.build_opener(*handler)
    opener.server = server
    return opener

