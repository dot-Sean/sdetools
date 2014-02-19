# NOTE: Before running ensure that the options are set properly in the
#       configuration file



from rational_response_generator import RationalResponseGenerator
from sdetools.alm_integration.tests.alm_plugin_test_base import AlmPluginTestBase
from sdetools.modules.sync_rational.rational_plugin import RationalConnector, RationalAPI


class TestRationalCase(AlmPluginTestBase):
    @classmethod
    def setUpClass(cls):
        alm_classes = [RationalConnector, RationalAPI, RationalResponseGenerator]
        super(TestRationalCase, cls).setUpClass(alm_classes=alm_classes)

    def test_update_existing_task_sde(self):
        """NOT SUPPORTED"""
        pass

    def assertEqual(self, item1, item2, error_msg):
        if item1 != item2:
            raise AssertionError(error_msg)

    def test_update_task_status_to_done(self):
        """TEST: Update SDE Task Status to DONE"""

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
        """TEST: Update SDE Task Status to TODO"""

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
        """TEST: Synchronize Task present only in SDE"""

        self.connector.config['conflict_policy'] = 'alm'
        self.connector.config['alm_phases'] = ['requirements', 'testing', 'development']
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task(priority=8)
        self.connector.synchronize()
        alm_task = self.connector.alm_get_task(test_task)
        self.assertEqual(test_task['id'][test_task['id'].find('T'):], alm_task.get_task_id(), 'Files don\'t match, mismatch: %s - %s' % (test_task['id'][test_task['id'].find('T'):], alm_task.get_task_id()))
        self.assertEqual(test_task['status'], alm_task.get_status(), 'Files don\'t match, mismatch: %s - %s' % (test_task['status'], alm_task.get_status()))


"""
    def test_parsing_alm_task(self):
        result = super(TestRationalCase, self).test_parsing_alm_task()
        test_task = result[0]
        test_task_result = result[1]
        alm_id = test_task['id'].split('T')[1]
        result_alm_id = test_task_result.get_alm_id()

        self.assertEqual(result_alm_id, alm_id, 'Expected alm_id %s, got %s' % (alm_id, result_alm_id))


    def test_parse_non_done_status_as_todo(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)
        test_task_result.status = "Non-done status"


        self.assertEqual(test_task_result.get_status(), "TODO", 'Expected status to default to TODO')

    def test_invalid_api_token(self):
        self.mock_alm_response.set_response_flags({'get_user': '401'})
        self.connector.config['alm_api_token'] = 'testApiToken'

        exception_msg = 'Unable to connect to GitHub service (Check server URL, api token). Reason: '\
                        'HTTP Error 401. Explanation returned: FATAL ERROR: Requires authentication'

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect_server)

    def test_invalid_user_pass(self):
        self.mock_alm_response.set_response_flags({'get_user': '401'})
        self.connector.config['alm_api_token'] = ''
        exception_msg = 'Unable to connect to GitHub service (Check server URL, user, pass). Reason: '\
                        'HTTP Error 401. Explanation returned: FATAL ERROR: Requires authentication'

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_connect_server)

    def test_invalid_field(self):
        self.mock_alm_response.set_response_flags({'post_issue': '422'})
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        exception_msg = 'Unable to add task %s to GitHub. Reason: HTTP Error 422. Explanation returned: FATAL ERROR: Validation Failed. ' \
                        'Additional Info - The field "title" is required for the resource "Issue"' % test_task['id']

        self.assert_exception(AlmException, '', exception_msg, self.connector.alm_add_task, test_task)

"""