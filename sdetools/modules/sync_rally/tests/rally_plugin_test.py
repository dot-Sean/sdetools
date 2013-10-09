# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import os
import unittest
from datetime import datetime
from rally_response_generator import RallyResponseGenerator

import sdetools.alm_integration.tests.alm_mock_response
import sdetools.alm_integration.tests.alm_mock_sde_plugin
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response
MOCK_SDE = sdetools.alm_integration.tests.alm_mock_sde_plugin


class TestRallyCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path_to_rally_connector = 'sdetools.modules.sync_rally.rally_plugin'
        current_dir = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(current_dir, CONF_FILE_LOCATION)
        super(TestRallyCase, cls).setUpClass(path_to_rally_connector, conf_path)

    def init_alm_connector(self):
        connector = RallyConnector(self.config, RallyAPIBase(self.config))
        super(TestRallyCase, self).init_alm_connector(connector)

    def post_parse_config(self):
        response_generator = RallyResponseGenerator(self.config['alm_server'],
                                                    self.config['alm_method'])

        MOCK_RESPONSE.patch_call_rest_api(response_generator, self.path_to_alm_connector)

    def test_parsing_alm_task(self):
        result = super(TestRallyCase, self).test_parsing_alm_task()
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
