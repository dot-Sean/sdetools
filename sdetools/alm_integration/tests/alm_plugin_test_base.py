import re

from sdetools.sdelib.mod_mgr import ReturnChannel
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod

import sdetools.alm_integration.tests.alm_mock_sde_plugin
import sdetools.alm_integration.tests.alm_mock_response
from sdetools.sdelib.commons import Error

MOCK_SDE = sdetools.alm_integration.tests.alm_mock_sde_plugin
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response


def stdout_callback(obj):
    print obj


class AlmPluginTestBase(object):
    @classmethod
    def setUpClass(cls, path_to_alm_connector, conf_path):
        cls.path_to_alm_connector = path_to_alm_connector
        cls.conf_path = conf_path
        MOCK_SDE.patch_sde_mocks(path_to_alm_connector)

    @abstractmethod
    def init_alm_connector(self, alm_connector):
        self.tac = alm_connector

    @abstractmethod
    def post_parse_config(self):
        """
             Setup steps needed after the config file has been parsed;
             such as setting up the response generator.
        """
        pass

    def setUp(self):
        """
            Plugin setup mirrors the setup that occurs during a sync_alm call
        """
        self.sde_tasks = None
        self.alm_tasks = None
        ret_chn = ReturnChannel(stdout_callback, {})
        self.config = Config('', '', ret_chn, 'import')

        self.init_alm_connector()
        Config.parse_config_file(self.config, self.conf_path)
        self.post_parse_config()
        self.tac.initialize()

    def tearDown(self):
        MOCK_RESPONSE.response_generator_clear_tasks()
        MOCK_RESPONSE.set_response_flags({})

    def test_parsing_alm_task(self):
        # Verify that none of the abstract methods inherited from AlmTask will break.
        # This test can be extended to verify the contents of task.
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        test_task_result = self.tac.alm_get_task(test_task)

        task_id = test_task_result.get_task_id()
        regex = 'C?T[0-9a-zA-z]+$'

        self.assertMatch(regex, task_id,
                         'Task id does not match the expected pattern. pattern:%s, task_id:%s' % (regex, task_id))
        test_task_result.get_priority()
        test_task_result.get_alm_id()
        test_task_result.get_status()
        test_task_result.get_timestamp()

        return [test_task, test_task_result]

    def test_alm_connect(self):
        self.tac.alm_connect()

    def test_add_and_get_task(self):
        # The plugin may initialize variables during alm_connect() so we need
        # to call alm_connect() before proceeding
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        test_task_result = self.tac.alm_get_task(test_task)

        self.assertNotNone(test_task_result, 'Failed retrieve newly added task')

    def test_update_task_status_to_done(self):
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'DONE',
                            'Cannot update task status to DONE because status is already DONE')

        self.tac.alm_update_task_status(alm_task, 'DONE')
        test_task_result = self.tac.alm_get_task(test_task)

        self.assertEqual(test_task_result.get_status(), 'DONE', 'Failed to update task status to DONE')

    def test_update_task_status_to_na(self):
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'NA', 'Cannot update task status to NA because status is already NA')

        self.tac.alm_update_task_status(alm_task,'NA')
        test_task_result = self.tac.alm_get_task(test_task)

        self.assertIn(test_task_result.get_status(), ['DONE', 'NA'], 'Failed to update task status to NA')

    def test_update_task_status_to_todo(self):
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        test_task['status'] = 'DONE'
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'TODO',
                            'Cannot update task status to TODO because status is already TODO')

        self.tac.alm_update_task_status(alm_task, 'TODO')
        test_task_result = self.tac.alm_get_task(test_task)

        self.assertEqual(test_task_result.get_status(), 'TODO', 'Failed to update task status to TODO')

    def test_synchronize(self):
        # Verify no exceptions are thrown
        self.tac.synchronize()

    @staticmethod
    def assertIn(value, expectations, msg=None):
        if not value in expectations:
            if not msg:
                msg = 'Value %s is not one of the following expected values: %s' % (value, expectations)

            raise AssertionError(msg)

    @staticmethod
    def assertNotNone(obj, msg=None):
        if obj is None:
            if not msg:
                msg = 'Expected None, got %s' % obj

            raise AssertionError(msg)

    @staticmethod
    def assertMatch(regex, str, msg):
        pattern = re.compile(regex)
        result = pattern.match(str)

        if not result:
            if not msg:
                msg = 'String %s did not match the following regular expression: %s' % (str, regex)

            raise AssertionError(msg)

    def assert_exception(self, exception, error_code, reason, fn, *args):
        if not exception:
            raise AssertionError('No exception type specified')
        if not fn:
            raise AssertionError('No function specified')
        if not exception and not error_code:
            raise AssertionError('No error code or error message to assert against')

        try:
            fn.__call__(*args)
            raise AssertionError('Expected an exception to be thrown')
        except Error, err:
            self.assertEqual(type(err), exception, 'Expected exception type %s, Got %s' % (exception, type(err)))

            if error_code:
                self.assertEqual(err.code, error_code, 'Expected error code %s, Got %s' % (error_code, err.code))
            if reason:
                self.assertTrue(reason in err.value, "Expected error message '%s', Got '%s'" % (reason, err.value))
