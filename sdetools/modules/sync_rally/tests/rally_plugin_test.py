# NOTE: Before running ensure that the options are set properly in the
#       configuration file
import unittest

from rally_response_generator import RallyResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_rally.rally_plugin import RallyConnector, RallyAPIBase, AlmException
PATH_TO_ALM_REST_API = 'sdetools.modules.sync_rally.rally_plugin'


class TestRallyCase(AlmPluginTestBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [RallyConnector, RallyAPIBase, RallyResponseGenerator]
        super(TestRallyCase, cls).setUpClass(alm_classes=alm_classes)

    def test_parsing_alm_task(self):
        result = super(TestRallyCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]

        alm_id = test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))

    def test_subscription_error(self):
        self.mock_alm_response.set_response_flags({'get_subscription': '401'})

        self.assert_exception(AlmException, '', 'Unable to retrieve subscription from Rally.',
                              self.connector.alm_connect_project)

    def test_invalid_card_type(self):
        self.config['rally_card_type'] = 'BAD_CARD_TYPE'

        self.assert_exception(AlmException, '', 'Invalid configuration for rally_card_type. Expected "Story"',
                              self.connector.alm_connect_project)

    def test_invalid_new_status(self):
        bad_status = 'INVALID_NEW_STATUS'
        allowed_statuses = [u'Defined', u'In-Progress', u'Completed', u'Accepted']
        self.config['rally_new_status'] = bad_status

        self.assert_exception(AlmException, '', 'Invalid rally_new_status "%s". Expected one of %s' %
                                                (bad_status, allowed_statuses), self.connector.alm_connect_project)

    def test_invalid_done_statuses(self):
        bad_status = ['INVALID_DONE_STATUS']
        allowed_statuses = [u'Defined', u'In-Progress', u'Completed', u'Accepted']
        self.config['rally_done_statuses'] = bad_status

        self.assert_exception(AlmException, '', 'Invalid rally_done_statuses %s. Expected one of %s' %
                                                (bad_status, allowed_statuses), self.connector.alm_connect_project)



