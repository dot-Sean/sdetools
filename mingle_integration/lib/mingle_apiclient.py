import sys, os

sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

import urllib
import urllib2
import base64

from sdelib.apiclient import APIError, APIHTTPError, APICallError, APIAuthError
from sdelib.apiclient import APIFormatError, ServerError, URLRequest, APIBase
from xml.dom import minidom

class MingleAPIBase(APIBase):
    def __init__(self, config):
        self.config = config
        self.base_uri = '%s://%s/api/v2/projects/%s' %(self.config['method'],
                self.config['alm_server'], self.config['alm_project'])
        self.proxy_uri = '%s://%s:%s@%s/' % (self.config['method'],
                self.config['alm_id'], self.config['alm_password'],
                self.config['alm_server'])
        handler_func = (urllib2.HTTPSHandler if self.config['method'] == 'https' else
                 urllib2.HTTPHandler)
        handler = handler_func(debuglevel=config['debug'])
        self.opener = urllib2.build_opener(handler)

    def _call_api(self, target, method=URLRequest.GET, args=None):
        """
        Internal method used to call a RESTFul API

        Keywords:
        target - the path of the API call (without host name)
        method -  HTTP Verb, specified by the URLRequest class. Default
                  is GET
        args - A dictionary of post paramters in format { 'key1':'value1', 'key2':'value2'}
        """
        req_url = '%s/%s' % (self.base_uri, target)
        if not args:
            args = {}
        data = None
        if method == URLRequest.GET:
            if args:
                req_url = '%s?%s' % (req_url, urllib.urlencode(args))
        else:
            data = urllib.urlencode(args)
        req = URLRequest(req_url, data=data, method=method)
        encoded_auth = base64.encodestring('%s:%s' % (self.config['alm_id'], self.config['alm_password']))[:-1]
        authheader =  "Basic %s" % (encoded_auth)
        req.add_header("Authorization", authheader)

        call_success = True
        try:
            handle = self.opener.open(req)
        except IOError, e:
            handle = e
            call_success = False

        if not call_success:
            if not hasattr(handle, 'code'):
                raise ServerError('Invalid server or server unreachable.')
            err_msg = 'Unknown Error'
            try:
                err_ret = handle.read()
            except:
                pass
            if (handle.code == 401 or handle.code == 404):
                raise APIAuthError
            raise APICallError(handle.code, "Error")

        result = ''
        while True:
            res_buf = handle.read()
            if not res_buf:
                break
            result += res_buf
        handle.close()

        try:
            if (result != ''):
                result = minidom.parseString(result)
        except Exception as e:
           #This means that the result doesn't have XML, not an error
            pass
        return result
