# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from pt_response_generator import PivotalTrackerResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_pt.pt_plugin import PivotalTrackerConnector, PivotalTrackerAPI, AlmException


class TestPivotalTrackerCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [PivotalTrackerConnector, PivotalTrackerAPI, PivotalTrackerResponseGenerator]
        super(TestPivotalTrackerCase, cls).setUpClass(alm_classes=alm_classes)

    def test_parsing_alm_task(self):
        result = super(TestPivotalTrackerCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_invalid_story_type(self):
        self.config['pt_story_type'] = 'BAD_STORY_TYPE'
        valid_types = ['feature', 'bug', 'chore']

        self.assert_exception(AlmException, '', 'Invalid %s %s. Expected one of %s.' %
                              ('pt_story_type', 'BAD_STORY_TYPE', valid_types), self.connector.alm_connect)

    def test_invalid_new_status(self):
        self.config['pt_new_status'] = 'BAD_STATUS'
        valid_types = ['unstarted', 'unscheduled', 'started']

        self.assert_exception(AlmException, '', 'Invalid %s %s. Expected one of %s.' %
                              ('pt_new_status', 'BAD_STATUS', valid_types), self.connector.alm_connect)

    def test_invalid_done_statuses(self):
        self.config['pt_done_statuses'] = ['BAD_STATUS', 'accepted']
        valid_types = ['accepted', 'delivered', 'finished']

        self.assert_exception(AlmException, '', 'Invalid %s %s. Expected one of %s.' %
                              ('pt_done_statuses', set(['BAD_STATUS']), valid_types), self.connector.alm_connect)

    def test_invalid_chore_done_status(self):
        self.config['pt_done_statuses'] = ['finished']
        self.config['pt_story_type'] = 'chore'

        self.assert_exception(AlmException, '', 'Chores only have one completion state - "accepted"',
                              self.connector.alm_connect)

    def test_pt_add_feature_story(self):
        self.config['conflict_policy'] = 'sde'
        self.config['pt_story_type'] = 'feature'
        self.config['pt_new_status'] = 'started'
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task(status='DONE')
        self.connector.alm_add_task(test_task)

        # If we do not auto-assign an estimate when adding a new 'feature' with the 'started' state, this test will fail

    def test_pt_update_feature_story(self):
        self.config['conflict_policy'] = 'sde'
        self.config['pt_story_type'] = 'feature'
        self.config['pt_new_status'] = 'unstarted'
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task(status='TODO')
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'DONE', 'Cannot update task status to DONE because status is already DONE')

        self.connector.alm_update_task_status(alm_task, 'DONE')

        # If we do not auto-assign an estimate when updating an unestimated 'feature', this test will fail