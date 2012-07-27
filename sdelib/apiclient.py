import urllib
import urllib2
import base64

from commons import json

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
        """
        Internal method used to call a RESTFul API

        Keywords:
        target - the path of the API call (without host name)
        method -  HTTP Verb, specified by the URLRequest class. Default
                  is GET
        args - JSON Data for arguments

        """
        req_url = '%s/%s' % (self.base_uri, target)
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
        elif self.auth_mode == 'basic':
            encoded_auth = base64.encodestring('%s:%s' % (self.config['email'], self.config['password']))[:-1]
            authheader =  "Basic %s" % (encoded_auth)
            req.add_header("Authorization", authheader)
        elif self.auth_mode == 'session':
            if not self.session_info:
                return -105, 'Session not setup or invalid'
            cookies = {self.session_info['session-cookie-name']: self.session_info['session-token']}
            if method != URLRequest.GET:
                #TODO: This should be removed on the server side
                req.add_header('Referer', self.base_uri)
                req.add_header(self.session_info['csrf-header-name'], self.session_info['csrf-token'])
                cookies[self.session_info['csrf-cookie-name']] = self.session_info['csrf-token']
            cookie_str = '; '.join(['%s=%s' % (x, cookies[x]) for x in cookies])
            req.add_header('Cookie', cookie_str)
        else:
            return -103, 'Unknown Authentication mode.'

        try:
            handle = self.opener.open(req)
        except IOError, e:
            if not hasattr(e, 'code'):
                return -101, 'Invalid server or server unreachable.'
            if e.code == 401:
                return e.code, 'Invalid Email/Password.'
            return e.code, 'Unknown Error'

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
            return -102, 'Unable to process JSON data.'

        return 0, result

    def start_session(self):
        """ 
        Starts a session with configured email & password in SD Elements
        """
        
        args = {
            'username': self.config['email'],
            'password': self.config['password']}
        ret_err, ret_val = self._call_api('session', URLRequest.PUT, args=args)
        for key in ['session-cookie-name', 'csrf-token', 'csrf-header-name', 
            'csrf-cookie-domain', 'csrf-cookie-name', 'session-token']:
            if key not in ret_val:
                return -104, 'Invalid session information structure.'
        self.session_info = ret_val
        self.auth_mode = 'session'
        return 0, 'Session established.'

    def get_applications(self, **filters):
        """
        Gets all applications accessible to user 

        Available Filters:
            name -> application name to be searched for
        """
        ret_err, ret_val = self._call_api('applications', args=filters)
        if ret_err:
            return ret_err, ret_val
        return 0, ret_val['applications']
    
    def get_projects(self, application, **filters):
        """
        Gets all projects for parameter application
        
        Available Filters:
            name -> project name to be searched for
        """
        args = {'application':application}
        args.update(filters)
        ret_err, ret_val = self._call_api('projects', args=args)
        if ret_err:
            return ret_err, ret_val
        return 0, ret_val['projects']

    def get_tasks(self, project):
        """ Gets all tasks in parameter project"""
        ret_err, ret_val = self._call_api('tasks', args={'project':project})
        if ret_err:
            return ret_err, ret_val
        return 0, ret_val['tasks']

    def get_task(self, task):
        """ Gets an individual task with parameter task id"""
        ret_err, ret_val = self._call_api('tasks/%s' % task)
        if ret_err:
            return ret_err, ret_val
        return 0, ret_val

    def add_note(self, task, text, filename, status):
        """ Adds a note to task with given text, filename and status """
        note = {'text':text, 'filename':filename, 'status':status, 'task':task}
        ret_err, ret_val = self._call_api('notes', URLRequest.POST, args=note)
        if ret_err:
            return ret_err, ret_val
        return 0, ret_val

    def update_task_status(self, task, status):
        """
        Update the task status. The task ID should include the project number
        """
        #TODO: regular expression on task and status for validation
        ret_err, ret_val = self._call_api('tasks/%s' % task, URLRequest.PUT,
            args={'status':status})
        if ret_err:
            return ret_err, ret_val
        return 0, ret_val['status']
