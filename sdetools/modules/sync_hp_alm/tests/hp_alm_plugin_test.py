# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from hp_alm_response_generator import HPAlmResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_hp_alm.hp_alm_plugin import HPAlmConnector, HPAlmAPIBase


class TestHPAlmCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [HPAlmConnector, HPAlmAPIBase, HPAlmResponseGenerator]
        super(TestHPAlmCase, cls).setUpClass(alm_classes=alm_classes)

    def test_parsing_alm_task(self):
        result = super(TestHPAlmCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_add_test_plan(self):
        self.config['alm_phases'] = 'requirement,testing'
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task(phase='testing')
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertNotNone(test_task_result, 'Failed to add test plan')

        alm_id = test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_add_requirement_coverage(self):
        self.config['alm_phases'] = 'requirements,testing'
        test_task = self.mock_sde_response.generate_sde_task(phase='testing')
        requirement_task = self.mock_sde_response.generate_sde_task(phase='requirement')
        self.connector.synchronize()
        hp_requirement_id = self.connector.alm_get_task(requirement_task).get_alm_id()
        hp_test_id = self.connector.alm_get_task(test_task).get_alm_id()
        uncovered_id = '9999999999999999999999'
        uncovered_requirements = self.connector._get_uncovered_requirements(hp_test_id, [hp_requirement_id, uncovered_id])

        self.assertIn(uncovered_id, uncovered_requirements, 'Expected an uncovered requirement')
        self.assertTrue(hp_requirement_id not in uncovered_requirements, 'Expected to find a requirement coverage for '
                'test id %s and requirement id %s' % (hp_test_id, hp_requirement_id))

    def test_update_test_plan_status(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task(phase='testing')
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'DONE', 'Cannot update task status to DONE because status is already DONE')

        self.connector.alm_update_task_status(alm_task, 'DONE')
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertEqual(test_task_result.get_status(), 'TODO', 'Should not have been able to update the status of a test plan')