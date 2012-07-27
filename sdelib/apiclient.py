import urllib
import urllib2
import base64

from commons import json, Error, UsageError

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
    def __init__(self):
        APIError.__init__(self, 'Incorrect Email/Password')

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

class APIBase:
    def __init__(self, config):
        self.config = config
        self.base_uri = '%s://%s/api' % (self.config['method'], self.config['server'])
        self.app = None
        self.prj = None
        self.auth_mode = 'basic'
        self.session_info = None

        if self.config['method'] == 'https':
            handler_func = urllib2.HTTPSHandler
        else:
            handler_func = urllib2.HTTPHandler

        handler = handler_func(debuglevel=config['debug'])
        self.opener = urllib2.build_opener(handler)

    def _call_api(self, target, method=URLRequest.GET, args=None):
        req_url = '%s/%s' % (self.base_uri, target)
        auth_mode = self.auth_mode
        if not args:
            args = {}
        data = None

        if method == URLRequest.GET:
            if args:
                req_url = '%s?%s' % (req_url, urllib.urlencode(args))
        else:
            data = json.dumps(args)
        req = URLRequest(req_url, data=data, method=method)

        if (method != URLRequest.GET):
            req.add_header('Content-Type','application/json')

        if target == 'session':
            pass
        elif auth_mode == 'basic':
            encoded_auth = base64.encodestring('%s:%s' % (self.config['email'], self.config['password']))[:-1]
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
            raise UsageError('Unknown Authentication mode.')

        call_success = True
        try:
            handle = self.opener.open(req)
        except IOError, e:
            handle = e
            call_success = False

        if not call_success:
            if not hasattr(handle, 'code'):
                #TODO
                raise ServerError('Invalid server or server unreachable.')
            err_msg = 'Unknown Error'
            try:
                err_ret = handle.read()
                err_msg = json.loads(err_ret)['error']
            except:
                pass
            if handle.code == 401:
                raise APIAuthError
            raise APICallError(handle.code, err_msg)

        result = ''
        while True:
            res_buf = handle.read()
            if not res_buf:
                break
            result += res_buf
        handle.close()

        try:
            result = json.loads(result)
        except:
            raise APIFormatError('Unable to process JSON data.')

        return result

    def start_session(self):
        args = {
            'username': self.config['email'],
            'password': self.config['password']}
        try:
            result = self._call_api('session', URLRequest.PUT, args=args)
        except APIHTTPError, e:
            if e.code == 400:
                raise APIAuthError
            raise
        for key in ['session-cookie-name', 'csrf-token', 'csrf-header-name', 
            'csrf-cookie-domain', 'csrf-cookie-name', 'session-token']:
            if key not in result:
                raise APIFormatError('Invalid session information structure.')
        self.session_info = result
        self.auth_mode = 'session'

    def get_applications(self, **filters):
        """
        Available Filters:
            name -> application name to be searched for
        """
        result = self._call_api('applications', args=filters)
        return result['applications']
    
    def get_projects(self, application, **filters):
        """
        Available Filters:
            name -> project name to be searched for
        """
        args = {'application':application}
        args.update(filters)
        result = self._call_api('projects', args=args)
        return result['projects']

    def get_tasks(self, project):
        result = self._call_api('tasks', args={'project':project})
        return result['tasks']

    def add_note(self, task, text, filename, status):
        note = {'text':text, 'filename':filename, 'status':status, 'task':task}
        result = self._call_api('notes', URLRequest.POST, args=note)
        return result

    def update_task_status(self, task, status):
        """
        Update the task status. The task ID should include the project number
        """
        #TODO: regular expression on task and status for validation
        result = self._call_api('tasks/%s' % task, URLRequest.PUT,
            args={'status':status})
        return result['status']
