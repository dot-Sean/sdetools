# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import sys
import os
import unittest
from datetime import datetime
from hp_alm_response_generator import HPAlmResponseGenerator

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
import sdetools.alm_integration.tests.alm_mock_response
import sdetools.alm_integration.tests.alm_mock_sde_plugin
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_hp_alm.hp_alm_plugin import HPAlmConnector, HPAlmAPIBase, AlmException

CONF_FILE_LOCATION = 'test_settings.conf'
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response
MOCK_SDE = sdetools.alm_integration.tests.alm_mock_sde_plugin


class TestHPAlmCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        path_to_hp_alm_connector = 'sdetools.modules.sync_hp_alm.hp_alm_plugin'
        current_dir = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(current_dir, CONF_FILE_LOCATION)
        super(TestHPAlmCase, self).setUpClass(path_to_hp_alm_connector, conf_path)

    def init_alm_connector(self):
        connector = HPAlmConnector(self.config, HPAlmAPIBase(self.config))
        super(TestHPAlmCase, self).init_alm_connector(connector)

    def post_parse_config(self):
        response_generator = HPAlmResponseGenerator(self.config['hp_alm_domain'],
                                                    self.config['alm_project'],
                                                    self.config['alm_user'])

        MOCK_RESPONSE.patch_call_rest_api(response_generator, self.path_to_alm_connector)

    def test_parsing_alm_task(self):
        result = super(TestHPAlmCase, self).test_parsing_alm_task()
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
