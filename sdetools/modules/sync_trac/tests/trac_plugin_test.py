# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import os
import unittest

from datetime import datetime
from mock import patch
from functools import partial
from trac_response_generator import TracResponseGenerator
from sdetools.sdelib.testlib.alm_mock_response import MOCK_ALM_RESPONSE
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_trac.trac_plugin import TracConnector, TracXMLRPCAPI


class MockProxyMethods():
    def __init__(self, cls_name):
        self.cls_name = cls_name

    def __getattr__(self, method_name):
        target = '%s.%s' % (self.cls_name, method_name)
        return partial(self.get_response, target, MOCK_ALM_RESPONSE.get_response_flags())

    @staticmethod
    def get_response(*args):
        return MOCK_ALM_RESPONSE.get_response_generator().get_proxy_response(args)


class MockXMLRPCProxy():
    def __init__(self, base_uri):
        pass

    def __getattr__(self, name):
        return MockProxyMethods(name)


class TestTracCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path_to_alm_rest_api = 'sdetools.modules.sync_trac.trac_plugin'
        cls.current_dir = os.path.dirname(os.path.realpath(__file__))
        super(TestTracCase, cls).setUpClass()

    def init_alm_connector(self):
        super(TestTracCase, self).init_alm_connector(TracConnector(self.config, TracXMLRPCAPI(self.config)))

    def init_response_generator(self):
        super(TestTracCase, self).init_response_generator(TracResponseGenerator())

    def post_parse_config(self):
        patch('%s.xmlrpclib.ServerProxy' % self.path_to_alm_rest_api, MockXMLRPCProxy).start()

    def test_parsing_alm_task(self):
        result = super(TestTracCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = test_task['id'].split('T')[1]
        alm_status = test_task['status']
        result_alm_id = test_task_result.get_alm_id()
        result_status = test_task_result.get_status()
        result_timestamp = test_task_result.get_timestamp()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))
        self.assertEqual(result_status, alm_status, 'Expected %s status, got %s' % (alm_status, result_status))
        self.assertEqual(type(result_timestamp), datetime, 'Expected a datetime object')
