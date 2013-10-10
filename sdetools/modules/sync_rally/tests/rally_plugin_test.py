# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from datetime import datetime
from rally_response_generator import RallyResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase
PATH_TO_ALM_REST_API = 'sdetools.modules.sync_rally.rally_plugin'


class TestRallyCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestRallyCase, cls).setUpClass(PATH_TO_ALM_REST_API)

    def init_alm_connector(self):
        super(TestRallyCase, self).init_alm_connector(RallyConnector(self.config, RallyAPIBase(self.config)))

    def init_response_generator(self):
        super(TestRallyCase, self).init_response_generator(RallyResponseGenerator(self.config, self.test_dir))

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
