import sys
import os
import unittest
from datetime import datetime
from mingle_response_generator import MingleResponseGenerator

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
import sdetools.alm_integration.tests.alm_mock_response
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_mingle.mingle_plugin import MingleConnector, MingleAPIBase

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response


class TestMingleCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        path_to_mingle_connector = 'sdetools.modules.sync_mingle.mingle_plugin'
        current_dir = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(current_dir, CONF_FILE_LOCATION)
        super(TestMingleCase, self).setUpClass(path_to_mingle_connector, conf_path)

    def init_alm_connector(self):
        connector = MingleConnector(self.config, MingleAPIBase(self.config))
        super(TestMingleCase, self).init_alm_connector(connector)

    def post_parse_config(self):
        response_generator = MingleResponseGenerator(self.config['alm_project'])

        MOCK_RESPONSE.patch_call_rest_api(response_generator, self.path_to_alm_connector)

    def test_parsing_alm_task(self):
        result = super(TestMingleCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        task_id = test_task['title']
        alm_id = int(test_task['id'].split('T')[1])
        alm_status = test_task['status']
        result_task_id = test_task_result.get_task_id()
        result_alm_id = test_task_result.get_alm_id()
        result_status = test_task_result.get_status()
        result_timestamp = test_task_result.get_timestamp()

        self.assertEqual(result_task_id, task_id, 'Expected task id %s, got %s' % (task_id, result_task_id))
        self.assertEqual(type(result_alm_id), int, 'Expected alm_id to be an integer')
        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))
        self.assertEqual(result_status, alm_status, 'Expected %s status, got %s' % (alm_status, result_status))
        self.assertEqual(type(result_timestamp), datetime, 'Expected a datetime object')


