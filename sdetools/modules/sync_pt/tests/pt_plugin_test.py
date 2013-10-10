# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import os
import unittest
from datetime import datetime
from pt_response_generator import PivotalTrackerResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_pt.pt_plugin import PivotalTrackerConnector, PivotalTrackerAPI


class TestPivotalTrackerCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path_to_alm_rest_api = 'sdetools.modules.sync_pt.pt_plugin'
        cls.current_dir = os.path.dirname(os.path.realpath(__file__))
        super(TestPivotalTrackerCase, cls).setUpClass()

    def init_alm_connector(self):
        super(TestPivotalTrackerCase, self).init_alm_connector(PivotalTrackerConnector(self.config, PivotalTrackerAPI(self.config)))

    def init_response_generator(self):
         super(TestPivotalTrackerCase, self).init_response_generator(response_generator = PivotalTrackerResponseGenerator(self.config['alm_project'],
                 self.config['alm_project_version'],
                 self.config['pt_group_label']))

    def test_parsing_alm_task(self):
        result = super(TestPivotalTrackerCase, self).test_parsing_alm_task()
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
