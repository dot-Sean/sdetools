import random

from mock import patch
from urllib2 import HTTPError
from sdetools.sdelib.restclient import URLRequest, APIError
from sdetools.sdelib.testlib.sde_response_generator import SdeResponseGenerator
from sdetools.sdelib.sdeapi import ExtAPI


def mock_response_call_api(self, target, method=URLRequest.GET, args=None, call_headers={}, auth_mode=None):
    """
        If calling instance is ExtApi, use the sde response generator,
        else use alm response generator
    """
    if type(self) == ExtAPI:
        return MOCK_SDE_RESPONSE.call_api(self, target, method, args, call_headers, auth_mode)
    else:
        return MOCK_ALM_RESPONSE.call_api(self, target, method, args, call_headers, auth_mode)


class MockResponse(object):
    def __init__(self):
        self.response_generator = None
        self.response_flags = {}
        self.call_api_patch = None

    def initialize(self, response_generator, path_to_rest_api):
        self.response_generator = response_generator
        self.call_api_patch = patch('%s.RESTBase.call_api' % path_to_rest_api, mock_response_call_api)
        self.call_api_patch.start()

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
        self.get_response_generator().generator_clear_tasks()
        self.set_response_flags({})

        if self.call_api_patch is not None:
            self.call_api_patch.stop()

    def call_api(self, api_instance, target, method, args, call_headers, auth_mode):
        try:
            if self.get_response_generator() is None:
                raise APIError('Mock response has not been initialized yet')

            response = self.get_response_generator().get_response(target, self.get_response_flags(), args, method)

            if response and type(response) == dict and response.get('cookiejar'):
                api_instance.cookiejar.set_cookie(response.get('cookiejar'))

            return response
        except HTTPError, err:
            # Re-raise with more info
            err.url = '%s/%s' % (err.url, target)
            err.headers = call_headers
            raise APIError(err)


class MockSDEResponse(MockResponse):
    def initialize(self, config):
        path_to_sde_rest_api = 'sdetools.sdelib.sdeapi.restclient'
        response_generator = SdeResponseGenerator(config['sde_server'],
                                                  config['sde_application'],
                                                  config['sde_project'],
                                                  config['sde_method'])
        super(MockSDEResponse, self).initialize(response_generator, path_to_sde_rest_api)

    def generate_sde_task(self, task_number=None, project_id=1000, status='TODO', priority=7):
        return self.get_response_generator().generate_sde_task(task_number, project_id, status, priority)

MOCK_ALM_RESPONSE = MockResponse()
MOCK_SDE_RESPONSE = MockSDEResponse()
