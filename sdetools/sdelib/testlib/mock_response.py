from mock import patch
from urllib2 import HTTPCookieProcessor
from cookielib import Cookie
from types import StringType
from sdetools.sdelib.restclient import APIError
from sdetools.sdelib.testlib.sde_response_generator import SdeResponseGenerator

SDE_SERVER = None


class MockRequest(object):
    """ Mock Request object """
    def __init__(self, req, handles):
        if type(req) == StringType:
            self.method = 'GET'
            self.data = '{}'
            self.host = ''
            self.selector = req
            self.headers = []
        else:
            self.method = req.get_method()
            self.data = req.get_data()
            self.host = req.get_host()
            self.selector = req.get_selector()
            self.headers = req.header_items()
        self.handles = handles

        if self.host == SDE_SERVER:
            self.code, self.headers, self.response = MOCK_SDE_RESPONSE.get_response(self.selector, self.data, self.method, self.headers)
        else:
            self.code, self.headers, self.response = MOCK_ALM_RESPONSE.get_response(self.selector, self.data, self.method, self.headers)
        if isinstance(self.response, Cookie) and self.handles['cookiehandle']:
            self.handles['cookiehandle'].cookiejar.set_cookie(self.response)
            self.response = ''

    def read(self):
        response = self.response
        self.response = ''

        return response

    def close(self):
        pass


class MockOpener(object):
    """ Mock http_req.get_opener """
    def __init__(self, method, server, proxy, debuglevel):
        self.method = method
        self.server = server
        self.proxy = proxy
        self.debuglevel = debuglevel
        self.handles = {'cookiehandle': None, 'handles': []}

    def add_handler(self, handle):
        if isinstance(handle, HTTPCookieProcessor):
            self.handles['cookiehandle'] = handle
        else:
            self.handles['handles'].append(handle)

    def open(self, req):
        return MockRequest(req, self.handles)


class MockResponse(object):
    def __init__(self):
        self.response_generator = None
        self.response_flags = {}
        self.call_api_patch = None

    def initialize(self, response_generator):
        self.response_generator = response_generator
        self.call_api_patch = patch('sdetools.extlib.http_req.get_opener', self.mock_get_opener)
        self.call_api_patch.start()

    @staticmethod
    def mock_get_opener(method, server, proxy=None, debuglevel=0):
        return MockOpener(method, server, proxy, debuglevel)

    def set_response_flags(self, _response_flags):
        if type(_response_flags) == dict:
            self.response_flags = _response_flags
        else:
            raise APIError('Bad mock flag')

    def get_response_flags(self):
        return self.response_flags

    def get_response_generator(self):
        return self.response_generator

    def teardown(self):
        self.get_response_generator().generator_clear_resources()
        self.set_response_flags({})

        if self.call_api_patch is not None:
            self.call_api_patch.stop()

    def get_response(self, target, data, method, headers):
        return self.get_response_generator().get_response(target, self.get_response_flags(), data, method, headers)


class MockSDEResponse(MockResponse):
    def initialize(self, config):
        global SDE_SERVER
        if '@' in config['sde_api_token']:
            SDE_SERVER = config['sde_api_token'][config['sde_api_token'].find('@')+1:]
        else:
            SDE_SERVER = config['sde_server']
        response_generator = SdeResponseGenerator(config)
        super(MockSDEResponse, self).initialize(response_generator)

    def generate_sde_task(self, task_number=None, project_id=None, status='TODO', priority=7, phase='requirements',
                          tags=None):
        return self.get_response_generator().generate_sde_task(task_number, project_id, status, priority, phase, tags)

    def clear_tasks(self):
        return self.get_response_generator().generator_clear_resource('task')

    def clear_tasks(self):
        return self.get_response_generator().generator_clear_resource('task')

MOCK_ALM_RESPONSE = MockResponse()
MOCK_SDE_RESPONSE = MockSDEResponse()
