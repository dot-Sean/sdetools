import re
import os
import sys

from datetime import datetime
from sdetools.sdelib.mod_mgr import ReturnChannel
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.commons import abc, Error
from sdetools.sdelib.testlib.mock_response import MOCK_ALM_RESPONSE, MOCK_SDE_RESPONSE

abstractmethod = abc.abstractmethod
CONF_FILE_LOCATION = 'test_settings.conf'


def stdout_callback(obj):
    print obj


class AlmPluginTestBase(object):
    @classmethod
    def setUpClass(cls, path_to_alm_rest_api, test_dir=None, conf_file_location=CONF_FILE_LOCATION, alm_classes=[None, None, None]):
        """
            path_to_alm_rest_api - The import path of the class that extends RestBase
            test_dir             - The directory where we will look for the test config file.
                                   Default is the directory of the calling class
            conf_file_location   - The relative path from the test_dir to the conf file.
                                   Default is the value of CONF_FILE_LOCATION
            classes              - Pass the class name of the connector, api and response generator
                                   to use the default initializer.
                                   Expects:
                                        [alm_connector, alm_api, alm_response_generator
        """
        if test_dir is None:
            path_of_child_class = sys.modules[cls.__module__].__file__
            test_dir = os.path.dirname(path_of_child_class)

        cls.connector_cls, cls.api_cls, cls.generator_cls = alm_classes
        cls.test_dir = test_dir
        cls.conf_path = os.path.join(cls.test_dir, conf_file_location)
        cls.mock_sde_response = MOCK_SDE_RESPONSE
        cls.mock_alm_response = MOCK_ALM_RESPONSE
        cls.ret_chn = ReturnChannel(stdout_callback, {})
        cls.path_to_alm_rest_api = path_to_alm_rest_api

    def init_alm_connector(self):
        if self.connector_cls is None:
            raise Error('No alm connector found')
        elif self.api_cls is None:
            raise Error('No alm api found')
        else:
            self.connector = self.connector_cls(self.config, self.api_cls(self.config))

    def init_response_generator(self):
        if self.generator_cls is not None:
            self.response_generator = self.generator_cls(self.config, self.test_dir)
        else:
            raise Error('No response generator found')

    def pre_parse_config(self):
        pass

    def post_parse_config(self):
        pass

    def setUp(self):
        """
            Plugin setup mirrors the setup that occurs during a sync_alm call.
            Also initializes the mock responses.
        """
        self.config = Config('', '', self.ret_chn, 'import')
        self.init_alm_connector()
        self.pre_parse_config()

        Config.parse_config_file(self.config, self.conf_path)

        self.post_parse_config()
        self.init_response_generator()
        self.mock_sde_response.initialize(self.config)
        self.mock_alm_response.initialize(self.response_generator, self.path_to_alm_rest_api)
        self.connector.initialize()

    def tearDown(self):
        self.mock_alm_response.teardown()
        self.mock_sde_response.teardown()

    def test_parsing_alm_task(self):
        # Verify that none of the abstract methods inherited from AlmTask will break.
        # This test can be extended to verify the contents of task.
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)
        task_id = test_task_result.get_task_id()
        alm_id = test_task_result.get_alm_id()
        alm_status = test_task_result.get_status()
        alm_timestamp = test_task_result.get_timestamp()
        task_id_regex = 'C?T\d+$'

        self.assertMatch(task_id_regex, task_id, 'Task id does not match the expected pattern. pattern:%s, task_id:%s' %
                                                (task_id_regex, task_id))
        self.assertEqual(type(alm_timestamp), datetime, 'Expected a datetime object')
        self.assertEqual(test_task['status'], alm_status, 'Expected %s status, got %s' % (test_task['status'], alm_id))
        self.assertNotNone(alm_id, 'Expected a value for alm_id')

        return [test_task, test_task_result]

    def test_alm_connect(self):
        self.connector.alm_connect()

    def test_add_and_get_task(self):
        # The plugin may initialize variables during alm_connect() so we need
        # to call alm_connect() before proceeding
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertNotNone(test_task_result, 'Failed retrieve newly added task')

    def test_update_task_status_to_done(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'DONE',
                            'Cannot update task status to DONE because status is already DONE')

        self.connector.alm_update_task_status(alm_task, 'DONE')
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertEqual(test_task_result.get_status(), 'DONE', 'Failed to update task status to DONE')

    def test_update_task_status_to_na(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'NA', 'Cannot update task status to NA because status is already NA')

        self.connector.alm_update_task_status(alm_task,'NA')
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertIn(test_task_result.get_status(), ['DONE', 'NA'], 'Failed to update task status to NA')

    def test_update_task_status_to_todo(self):
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        test_task['status'] = 'DONE'
        print test_task['priority']
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'TODO',
                            'Cannot update task status to TODO because status is already TODO')

        self.connector.alm_update_task_status(alm_task, 'TODO')
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertEqual(test_task_result.get_status(), 'TODO', 'Failed to update task status to TODO')

    def test_synchronize(self):
        # Verify no exceptions are thrown
        self.connector.synchronize()

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
                msg = 'Expected a value other than None'

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
