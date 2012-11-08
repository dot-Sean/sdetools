import urllib
import urllib2
import base64

from commons import json, Error, UsageError
from extlib import sslcert_compat

import logging
logger = logging.getLogger(__name__)

CONF_OPTS = [
    ('%(prefix)s_user', 'Username for %(name)s Tool', None),
    ('%(prefix)s_pass', 'Password for %(name)s Tool', None),
    ('%(prefix)s_server', 'Server of the %(name)s', None),
    ('%(prefix)s_method', 'http vs https for %(name)s server', 'https'),
]

class APIError(Error):
    pass

class APIHTTPError(APIError):
    def __init__(self, code, msg):
        APIError.__init__(self, msg)
        self.code = code

    def __str__(self):
        return '%s (Error Code: %s)' % (Error.__str__(self), self.code)

class APICallError(APIHTTPError):
    pass

class APIAuthError(APIError):
    def __init__(self, msg=None):
        if not msg:
            msg = 'Incorrect Credentials'
        APIError.__init__(self, msg)

class ServerError(APIError):
    """
    Server reachability error (before HTTP is established)
    """
    pass

class APIFormatError(APIError):
    """
    API return format is not a proper JSON or is missing some needed fields
    """
    pass

class URLRequest(urllib2.Request):
    GET = 'GET'
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

class RESTBase(object):
    URLRequest = URLRequest

    APIError = APIError
    APIHTTPError = APIHTTPError
    APICallError = APICallError
    APIAuthError = APIAuthError
    ServerError = ServerError
    APIFormatError = APIFormatError

    def __init__(self, conf_prefix, conf_name, config, base_path):
        self.config = config
        self.base_path = base_path
        self.conf_prefix = conf_prefix
        self.conf_name = conf_name
        self.opener = None
        self._customize_config()

    def _get_conf(self, name):
        conf_name = '%s_%s' % (self.conf_prefix, name)
        return self.config[conf_name]

    def _customize_config(self):
        for var_name, desc, default in CONF_OPTS:
            self.config.add_custom_option(
                var_name % {'prefix': self.conf_prefix},
                desc % {'name': self.conf_name},
                default=default,
                group_name='%s Connector' % (self.conf_name))

    def post_conf_init(self):
        self.base_uri = '%s://%s/%s' % (self._get_conf('method'), 
                self._get_conf('server'), self.base_path)
        self.auth_mode = 'basic'
        self.session_info = None

        urllib_debuglevel = 0
        if __name__ in self.config['debug_mods']:
            urllib_debuglevel = 1

        handler = sslcert_compat.get_http_handler(self._get_conf('method'), debuglevel=urllib_debuglevel)
        self.opener = urllib2.build_opener(handler)

    def encode_post_args(self, args):
        return json.dumps(args)

    def parse_response(self, result):
        try:
            result = json.loads(result)
        except:
            raise APIFormatError('Unable to process JSON data.')
        return result

    def call_api(self, target, method=URLRequest.GET, args=None):
        """
        Internal method used to call a RESTFul API

        Keywords:
        target - the path of the API call (without host name)
        method -  HTTP Verb, specified by the URLRequest class. Default
                  is GET
        args - Data for arguments

        """
        if not self.opener:
            self.post_conf_init()

        logger.info('Calling API: %s %s' % (method, target))
        logger.debug(' + Args: %s' % ((repr(args)[:200]) + (repr(args)[200:] and '...')))
        req_url = '%s/%s' % (self.base_uri, target)
        auth_mode = self.auth_mode
        args = args or {}
        data = None

        if method == URLRequest.GET:
            if args:
                req_url = '%s?%s' % (req_url, urllib.urlencode(args))
        else:
            data = self.encode_post_args(args)
        req = URLRequest(req_url, data=data, method=method)

        if (method != URLRequest.GET):
            req.add_header('Content-Type','application/json')

        if target == 'session':
            pass
        elif auth_mode == 'basic':
            encoded_auth = base64.encodestring('%s:%s' % (self._get_conf('user'), self._get_conf('pass')))[:-1]
            authheader =  "Basic %s" % (encoded_auth)
            req.add_header("Authorization", authheader)
        elif auth_mode == 'session':
            if not self.session_info:
                raise UsageError('Session not setup or invalid (you need to call start_session first)')
            cookies = {self.session_info['session-cookie-name']: self.session_info['session-token']}
            if method != URLRequest.GET:
                #TODO: This should be removed on the server side
                req.add_header('Referer', self.base_uri)
                req.add_header(self.session_info['csrf-header-name'], self.session_info['csrf-token'])
                cookies[self.session_info['csrf-cookie-name']] = self.session_info['csrf-token']
            cookie_str = '; '.join(['%s=%s' % (x, cookies[x]) for x in cookies])
            req.add_header('Cookie', cookie_str)
        else:
            raise UsageError('Unknown Authentication mode "%s".' % (auth_mode))

        call_success = True
        try:
            handle = self.opener.open(req)
        except sslcert_compat.InvalidCertificateException, err:
            raise ServerError('Unable to verify SSL certificate for host: %s' % (self._get_conf('server')))
        except urllib2.URLError, err:
            handle = err
            call_success = False

        if not call_success:
            if not hasattr(handle, 'code'):
                raise ServerError('Invalid server or server unreachable: %s' % (self._get_conf('server')))
            try:
                err_msg = handle.read()
            except:
                err_msg = 'Unknown Error'
            try:
                err_msg = json.loads(err_msg)['error']
            except:
                # Not a JSON error
                pass
            if handle.code == 401:
                raise APIAuthError('Invalid Credentials for %s' % self.conf_name)
            raise APICallError(handle.code, err_msg)

        result = ''
        while True:
            res_buf = handle.read()
            if not res_buf:
                break
            result += res_buf
        handle.close()

        result = self.parse_response(result)

        return result

    def start_session(self):
        """
        Starts a session with configured email & password in SD Elements
        """

        args = {
            'username': self._get_conf('user'),
            'password': self._get_conf('pass')}
        try:
            result = self.call_api('session', URLRequest.PUT, args=args)
        except APIHTTPError, err:
            if err.code == 400:
                raise APIAuthError('Invalid Credentials for %s' % self.conf_name)
            raise
        for key in ['session-cookie-name', 'csrf-token', 'csrf-header-name',
            'csrf-cookie-domain', 'csrf-cookie-name', 'session-token']:
            if key not in result:
                raise APIFormatError('Invalid session information structure.')
        self.session_info = result
        self.auth_mode = 'session'
