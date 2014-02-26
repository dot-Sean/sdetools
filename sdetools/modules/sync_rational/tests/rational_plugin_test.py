# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from rational_response_generator import RationalResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_rational.rational_plugin import RationalConnector, RationalAPI


class TestRationalCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [RationalConnector, RationalAPI, RationalResponseGenerator]
        super(TestRationalCase, cls).setUpClass(alm_classes=alm_classes)

    def test_update_existing_task_sde(self):
        """NOT SUPPORTED"""
        pass

    def test_update_task_status_to_done(self):
        self.connector.config['conflict_policy'] = 'alm'
        self.connector.config['alm_phases'] = ['requirements', 'testing', 'development']
        self.connector.alm_connect()
        # Most of the module test configurations set the minimum priority to be 8
        # so we will create a task with this priority to make sure its in scope
        test_task = self.mock_sde_response.generate_sde_task(priority=8)
        test_task['status'] = 'DONE'
        self.connector.alm_add_task(test_task)
        self.connector.synchronize()
        the_task = self.connector.sde_get_task(test_task['id'])
        self.assertEqual(the_task['status'], 'DONE', 'Failed to update SDE task to DONE')

    def test_update_task_status_to_na(self):
        """TEST NOT APPLICABLE"""
        pass

    def test_update_task_status_to_todo(self):
        self.connector.config['conflict_policy'] = 'alm'
        self.connector.config['alm_phases'] = ['requirements', 'testing', 'development']
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task(priority=8)
        test_task['status'] = 'TODO'
        #print test_task
        self.connector.alm_add_task(test_task)
        self.connector.synchronize()
        the_task = self.connector.sde_get_task(test_task['id'])
        self.assertEqual(the_task['status'], 'TODO', 'Failed to update SDE task to TODO')

    def test_sync_no_alm_task(self):
        self.connector.config['conflict_policy'] = 'alm'
        self.connector.config['alm_phases'] = ['requirements', 'testing', 'development']
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task(priority=8)
        self.connector.synchronize()
        alm_task = self.connector.alm_get_task(test_task)
        self.assertEqual(test_task['id'][test_task['id'].find('T'):], alm_task.get_task_id(), 'Files don\'t match, mismatch: %s - %s' % (test_task['id'][test_task['id'].find('T'):], alm_task.get_task_id()))
        self.assertEqual(test_task['status'], alm_task.get_status(), 'Files don\'t match, mismatch: %s - %s' % (test_task['status'], alm_task.get_status()))

