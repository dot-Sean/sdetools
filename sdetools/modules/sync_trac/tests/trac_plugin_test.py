# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import os
import unittest

from datetime import datetime
from mock import patch
from functools import partial
from trac_response_generator import TracResponseGenerator

import sdetools.alm_integration.tests.alm_mock_response
import sdetools.alm_integration.tests.alm_mock_sde_plugin
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_trac.trac_plugin import TracConnector, TracXMLRPCAPI, AlmException

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response
MOCK_SDE = sdetools.alm_integration.tests.alm_mock_sde_plugin


class MockProxyMethods():
    def __init__(self, cls_name):
        self.cls_name = cls_name

    def __getattr__(self, method_name):
        target = '%s.%s' % (self.cls_name, method_name)
        return partial(self.get_response, target, MOCK_RESPONSE.get_response_flags())

    @staticmethod
    def get_response(*args):
        return MOCK_RESPONSE.get_response_generator().get_proxy_response(args)


class MockXMLRPCProxy():
    def __init__(self, base_uri):
        pass

    def __getattr__(self, name):
        return MockProxyMethods(name)


class TestTracCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        path_to_trac_connector = 'sdetools.modules.sync_trac.trac_plugin'
        current_dir = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(current_dir, CONF_FILE_LOCATION)
        super(TestTracCase, self).setUpClass(path_to_trac_connector, conf_path)

    def init_alm_connector(self):
        connector = TracConnector(self.config, TracXMLRPCAPI(self.config))
        super(TestTracCase, self).init_alm_connector(connector)

    def post_parse_config(self):
        response_generator = TracResponseGenerator()
        patch('sdetools.modules.sync_trac.trac_plugin.xmlrpclib.ServerProxy', MockXMLRPCProxy).start()
        MOCK_RESPONSE.patch_call_rest_api(response_generator, self.path_to_alm_connector)

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
