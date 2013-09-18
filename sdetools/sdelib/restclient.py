import urllib
import urllib2
import httplib
import base64
import cookielib

from commons import json, Error, UsageError
from sdetools.extlib import http_req

import logging
logger = logging.getLogger(__name__)

URLRequest = http_req.ExtendedMethodRequest

CONF_OPTS = [
    ['%(prefix)s_user', 'Username for %(name)s Tool', ''],
    ['%(prefix)s_pass', 'Password for %(name)s Tool', ''],
    ['%(prefix)s_server', 'Server of the %(name)s', ''],
    ['%(prefix)s_method', 'http vs https for %(name)s server', 'https'],
]

DEFAULT_API_TOKEN_HEADER_NAME = "X-Api-Token"

class APIError(Error):
    pass

class APIHTTPError(APIError):
    def __init__(self, code, msg):
        APIError.__init__(self, msg)
        self.code = code

    def __str__(self):
        return 'HTTP Error %s. Explanation returned: %s' % (self.code, Error.__str__(self).replace('\n', ''))

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

class RESTBase(object):
    """
    REST base class supports four authentication mode specified by auth_mode:
    - basic: HTTP Basic Auth using username and password
    - api_token: We use the _pass and allow customizing the API Token header name
    - session: Used mainly for SD Elements session
    - cookie: A cookie jar is added and cookies will be maintained
    """
    URLRequest = URLRequest

    APIError = APIError
    APIHTTPError = APIHTTPError
    APICallError = APICallError
    APIAuthError = APIAuthError
    ServerError = ServerError
    APIFormatError = APIFormatError

    def __init__(self, conf_prefix, conf_name, config, base_path=None, extra_conf_opts=[]):
        self._post_init_done = False
        self.config = config
        self.base_path = base_path
        self.conf_prefix = conf_prefix
        self.conf_name = conf_name
        self.opener = None
        self._auth_mode = 'basic'
        self.api_token_header_name = DEFAULT_API_TOKEN_HEADER_NAME
        self._customize_config(CONF_OPTS+extra_conf_opts)

    def _get_conf_name(self, name):
        return '%s_%s' % (self.conf_prefix, name)

    def _get_conf(self, name):
        return self.config[self._get_conf_name(name)]

    def _customize_config(self, conf_opts):
        for var_name, desc, default in conf_opts:
            self.config.add_custom_option(
                var_name % {'prefix': self.conf_prefix},
                desc % {'name': self.conf_name},
                default=default,
                group_name='%s Connector' % (self.conf_name))

    def set_auth_mode(self, auth_mode):
        if auth_mode not in ['basic', 'session', 'api_token', 'cookie']:
            raise UsageError('Invalid auth mode %s' % auth_mode)
        if auth_mode == self._auth_mode:
            return
        if auth_mode == 'session':
            self.start_session()
        elif auth_mode == 'cookie':
            if not self.opener:
                self.post_conf_init()
            self.cookiejar = cookielib.CookieJar()
            self.opener.add_handler(urllib2.HTTPCookieProcessor(self.cookiejar))
            
        self._auth_mode = auth_mode

    def urlencode_str(self, instr):
        return urllib.urlencode({'a':instr})[2:]

    def post_conf_init(self):
        if self._post_init_done:
            return

        for name in ['method', 'server']:
            if not self._get_conf(name):
                raise UsageError('Missing Configuration %s' % self._get_conf_name(name))

        urllib_debuglevel = 0
        if __name__ in self.config['debug_mods']:
            urllib_debuglevel = 1

        self.opener = http_req.get_opener(
            self._get_conf('method'),
            self._get_conf('server'),
            debuglevel=urllib_debuglevel)
        self.config[self._get_conf_name('server')] = self.opener.server

        self.session_info = None
        self.server = self._get_conf('server') 
        self.base_uri = '%s://%s' % (self._get_conf('method'), self.server)
        if self.base_path:
            self.base_uri = '%s/%s' % (self.base_uri, self.base_path)

        self._post_init_done = True

    def encode_post_args(self, args):
        return json.dumps(args)

    def parse_response(self, result):
        try:
            result = json.loads(result)
        except:
            raise APIFormatError('Unable to process JSON data: %s' % str(result)[:200])
        return result

    def parse_error(self, result):
        return json.loads(err_msg)['error']

    def set_content_type(self, req, method):
        if (method != URLRequest.GET):
            req.add_header('Content-Type','application/json')

    def get_custom_headers(self, target, method):
        """
        Override this to add your own custom headers
        """
        return []

    def generate_token_auth_header(self):
        """
        Override this to add your own custom authentication header
        Expected return value:
            [HEADER_NAME, HEADER_VALUE]
        """
        return [self.api_token_header_name, self._get_conf('pass')]

    def call_api(self, target, method=URLRequest.GET, args=None, call_headers={}, auth_mode=None):
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

        logger.info('Calling %s API: %s %s' % (self.conf_name, method, target))
        logger.debug(' + Args: %s' % ((repr(args)[:200]) + (repr(args)[200:] and '...')))
        req_url = '%s/%s' % (self.base_uri, target)
        if auth_mode is None:
            auth_mode = self._auth_mode
        args = args or {}
        data = None

        if method == URLRequest.GET:
            if args:
                req_url = '%s?%s' % (req_url, urllib.urlencode(args))
        else:
            data = self.encode_post_args(args)
        req = URLRequest(req_url, data=data, method=method)

        self.set_content_type(req, method)

        if auth_mode == 'api_token':
            authheader = self.generate_token_auth_header()
            req.add_header(authheader[0], authheader[1])
        elif target == 'session':
            pass
        elif auth_mode == 'cookie':
            # cookie jar will automatically handle this
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
        for item in call_headers:
            req.add_header(item, call_headers[item])
        for item, val in self.get_custom_headers(target, method):
            req.add_header(item, val)

        call_success = True
        try:
            handle = self.opener.open(req)
        except http_req.InvalidCertificateException, err:
            raise ServerError('Unable to verify SSL certificate for host: %s' % (self.server))
        except urllib2.URLError, err:
            handle = err
            call_success = False
        except httplib.InvalidURL, err:
            raise UsageError('Invalid URL. Reason %s' % (err))

        if not call_success:
            if not hasattr(handle, 'code'):
                raise ServerError('Invalid server or server unreachable: %s' % (self.server))
            try:
                err_msg = handle.read()
                logger.info('Error calling %s API. Raw error: %s' % (self.conf_name, repr(err_msg)[:200]))
            except:
                err_msg = 'Unknown Error'
            try:
                err_msg = self.parse_error(err_msg)
            except:
                # We fall back to unparsed version of the error
                pass
            if handle.code == 401:
                raise APIAuthError('Invalid Credentials for %s' % self.conf_name)
            raise APICallError(handle.code, err_msg[:255])

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
            result = self.call_api('session', URLRequest.PUT, args=args, auth_mode='basic')
        except APIHTTPError, err:
            if err.code == 400:
                raise APIAuthError('Invalid Credentials for %s' % self.conf_name)
            raise
        for key in ['session-cookie-name', 'csrf-token', 'csrf-header-name',
            'csrf-cookie-domain', 'csrf-cookie-name', 'session-token']:
            if key not in result:
                raise APIFormatError('Invalid session information structure.')
        self.session_info = result
