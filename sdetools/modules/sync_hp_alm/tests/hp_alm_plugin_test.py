# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import os
import unittest

from datetime import datetime
from hp_alm_response_generator import HPAlmResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_hp_alm.hp_alm_plugin import HPAlmConnector, HPAlmAPIBase


class TestHPAlmCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path_to_alm_rest_api = 'sdetools.modules.sync_hp_alm.hp_alm_plugin'
        cls.current_dir = os.path.dirname(os.path.realpath(__file__))
        super(TestHPAlmCase, cls).setUpClass()

    def init_alm_connector(self):
        super(TestHPAlmCase, self).init_alm_connector(HPAlmConnector(self.config, HPAlmAPIBase(self.config)))

    def init_response_generator(self):
        super(TestHPAlmCase, self).init_response_generator(HPAlmResponseGenerator(self.config['hp_alm_domain'],
                self.config['alm_project'], self.config['alm_user']))

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
