from mock import patch
from urllib2 import HTTPError
from sdetools.sdelib.restclient import URLRequest, APIError

mock_flag = None
alm_response_generator = None


def patch_call_rest_api(_alm_response_generator, path_to_alm_rest_plugin):
    global alm_response_generator
    alm_response_generator = _alm_response_generator
    patch('%s.RESTBase.call_api' % path_to_alm_rest_plugin, mock_call_rest_api).start()


def response_generator_clear_tasks():
    alm_response_generator.clear_alm_tasks()


def set_mock_flag(_mock_flag):
    global mock_flag
    mock_flag = _mock_flag


def get_response_generator():
    return alm_response_generator


def mock_call_rest_api(self, target, method=URLRequest.GET, args=None, call_headers={}):
    try:
        return alm_response_generator.get_response(target, mock_flag, args, method)
    except HTTPError, err:
        # Re-raise with more info
        err.url = '%s/%s' % (err.url, target)
        err.headers = call_headers
        raise APIError(err)
