import re
import os

from datetime import datetime
from sdetools.sdelib.mod_mgr import ReturnChannel, load_modules
from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.commons import abc, Error, get_directory_of_current_module, UsageError
from sdetools.sdelib.testlib.mock_response import MOCK_ALM_RESPONSE, MOCK_SDE_RESPONSE
from sdetools.alm_integration.alm_plugin_base import AlmException

abstractmethod = abc.abstractmethod
CONF_FILE_LOCATION = 'test_settings.conf'


def stdout_callback(obj):
    print obj


class AlmPluginTestBase(object):
    @classmethod
    def setUpClass(cls, test_dir=None, conf_file_location=CONF_FILE_LOCATION, alm_classes=[None, None, None]):
        """
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
            test_dir = get_directory_of_current_module(cls)

        cls.connector_cls, cls.api_cls, cls.generator_cls = alm_classes
        cls.test_dir = test_dir
        cls.conf_path = os.path.join(cls.test_dir, conf_file_location)
        cls.mock_sde_response = MOCK_SDE_RESPONSE
        cls.mock_alm_response = MOCK_ALM_RESPONSE
        cls.ret_chn = ReturnChannel(stdout_callback, {})

    def init_alm_connector(self):
        if self.connector_cls is None:
            raise Error('No alm connector found')
        elif self.api_cls is None:
            raise Error('No alm api found')
        else:
            self.connector = self.connector_cls(self.config, self.api_cls(self.config))

    def init_response_generator(self, resp_generator_cls=None):
        resp_generator_cls = resp_generator_cls or self.generator_cls
        if not resp_generator_cls:
            raise Error('No response generator found')
        self.response_generator = resp_generator_cls(self.config, self.test_dir)

    def pre_parse_config(self):
        pass

    def post_parse_config(self):
        pass

    def setUp(self):
        """
            Plugin setup mirrors the setup that occurs during a sync_alm call.
            Also initializes the mock responses.
        """
        command_list = load_modules()
        self.config = Config('help', '', command_list, [], self.ret_chn, 'shell')
        self.init_alm_connector()
        self.pre_parse_config()
        self.config.import_custom_options()
        Config.parse_config_file(self.config, self.conf_path)

        self.post_parse_config()
        self.init_response_generator()
        self.mock_sde_response.initialize(self.config)
        self.mock_alm_response.initialize(self.response_generator)
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
        task_id_regex = '^[^\d]+\d+$'

        self.assertMatch(task_id_regex, task_id, 'Task id does not match the expected pattern. pattern:%s, task_id:%s' %
                                                (task_id_regex, task_id))
        self.assertEqual(type(alm_timestamp), datetime, 'Expected a datetime object')
        self.assertEqual(test_task['status'], alm_status, 'Expected %s status, got %s' % (test_task['status'], alm_status))
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

    def test_alm_priority_map(self):
        priority_map_tests = [
            {
                'description': 'Single mapping',
                'map': {
                    '1-10': 'Simple'
                },
                'expected_pass': True
            },
            {
                'description': 'Three mappings',
                'map': {
                    '1-3': 'Low',
                    '4-6': 'Medium',
                    '7-10': 'High',
                },
                'expected_pass': True
            },
            {
                'description': 'Four mappings, out of order',
                'map': {
                    '1-3': 'Low',
                    '7-8': 'High',
                    '4-6': 'Medium',
                    '9-10': 'Critical',
                },
                'expected_pass': True
            },
            {
                'description': 'Priority 3 duplicated',
                'map': {
                    '1-3': 'Low',
                    '3-10': 'High',
                },
                'expected_pass': False
            },
            {
                'description': 'Priority 3 duplicated',
                'map': {
                    '1-3': 'Low',
                    '3': 'Medium',
                    '4-10': 'High',
                },
                'expected_pass': False
            },
            {
                'description': 'Priority 2 in wrong order',
                'map': {
                    '2-1': 'Low',
                    '3-10': 'High',
                },
                'expected_pass': False
            },
            {
                'description': 'Missing priority 3',
                'map': {
                    '1-2': 'Low',
                    '4-10': 'High',
                },
                'expected_pass': False
            },
            {
                'description': 'Priority 12 is out of range 1-10',
                'map': {
                    '1-12': 'Low',
                    '4-10': 'High',
                },
                'expected_pass': False
            },
            {
                'description': 'Priority 0 is out of range 1-10',
                'map': {
                    '0': 'Low',
                    '4-10': 'High',
                },
                'expected_pass': False
            },
            {
                'description': 'Priority 11 is out of range 1-10',
                'map': {
                    '1-10': 'Low',
                    '11': 'Super High',
                },
                'expected_pass': False
            }
        ]
        for priority_map_test in priority_map_tests:
            self.connector.config['test_alm'] = 'project'
            self.connector.config['alm_priority_map'] = priority_map_test['map']
            try:
                self.connector.initialize()
                if not priority_map_test['expected_pass']:
                    raise AssertionError('Error not detected for %s' % priority_map_test['description'])
            except AlmException:
                if priority_map_test['expected_pass']:
                    raise AssertionError('Unexpected exception thrown for %s' % priority_map_test['description'])

    def test_alm_test_connect(self):
        self.connector.config['test_alm'] = 'project'
        self.connector.synchronize()

    def test_sde_valid_phases(self):
        self.connector.initialize()
        self.connector.config['alm_phases'] = ['development', 'requirements']
        self.connector.synchronize()

    def test_sde_invalid_phases(self):
        self.connector.initialize()
        self.connector.config['alm_phases'] = ['development', 'invalid_phase']
        exception_msg = 'Incorrect alm_phase configuration: invalid_phase is not a valid phase'
        self.assert_exception(AlmException, '', exception_msg, self.connector.synchronize)

    def test_sde_invalid_selected_tasks(self):
        self.connector.config['selected_tasks'] = ['T123', '123']

        try:
            self.connector.initialize()
            raise Exception('Expected an exception to be thrown')
        except UsageError:
            pass

    def test_sde_invalid_min_priority(self):
        self.connector.config['sde_min_priority'] = 'BAD'
        exception_msg = 'Incorrect sde_min_priority specified in configuration. Valid values are > 0 and <= 10'
        self.assert_exception(AlmException, '', exception_msg, self.connector.initialize)

    def test_sde_too_small_min_priority(self):
        self.connector.config['sde_min_priority'] = 0
        exception_msg = 'Incorrect sde_min_priority specified in configuration. Valid values are > 0 and <= 10'
        self.assert_exception(AlmException, '', exception_msg, self.connector.initialize)

    def test_sde_too_large_min_priority(self):
        self.connector.config['sde_min_priority'] = 11
        exception_msg = 'Incorrect sde_min_priority specified in configuration. Valid values are > 0 and <= 10'
        self.assert_exception(AlmException, '', exception_msg, self.connector.initialize)

    def test_tasks_filter_tags(self):
        self.connector.config['conflict_policy'] = 'sde'
        self.connector.config['sde_min_priority'] = 1
        self.connector.config['sde_tags_filter'] = ['one', 'two']
        self.connector.sde_connect()
        self.connector.alm_connect()

        # clear out default tasks
        self.mock_sde_response.clear_tasks()

        self.mock_sde_response.generate_sde_task(priority=8, tags=['one', 'two', 'three'])
        self.mock_sde_response.generate_sde_task(priority=7, tags=['one'])
        self.mock_sde_response.generate_sde_task(priority=7, tags=['two'])
        self.mock_sde_response.generate_sde_task(priority=1, tags=['two', 'one'])
        self.mock_sde_response.generate_sde_task(priority=6, tags=['four', 'five'])

        tasks = self.connector.sde_get_tasks()
        self.assertTrue(len(tasks) == 5, 'Expected 3 tasks')

        tasks = self.connector.filter_tasks(tasks)
        self.assertTrue(len(tasks) == 2, 'Expected 2 tasks')

        for task in tasks:
            self.assertTrue(set(self.connector.config['sde_tags_filter']).issubset(task['tags']),
                            'Task %s has unexpected priority %d' % (task['id'], task['priority']))

    def test_tasks_filter_empty_tags(self):
        self.connector.config['conflict_policy'] = 'sde'
        self.connector.config['sde_min_priority'] = 1
        self.connector.config['sde_tags_filter'] = []
        self.connector.sde_connect()
        self.connector.alm_connect()

        # clear out default tasks
        self.mock_sde_response.clear_tasks()

        self.mock_sde_response.generate_sde_task(priority=8, tags=['one', 'two', 'three'])
        self.mock_sde_response.generate_sde_task(priority=7, tags=['one'])
        self.mock_sde_response.generate_sde_task(priority=7, tags=['two'])
        self.mock_sde_response.generate_sde_task(priority=1, tags=['two', 'one'])
        self.mock_sde_response.generate_sde_task(priority=6, tags=['four', 'five'])

        tasks = self.connector.sde_get_tasks()
        self.assertTrue(len(tasks) == 5, 'Expected 5 tasks')

        tasks = self.connector.filter_tasks(tasks)
        self.assertTrue(len(tasks) == 5, 'Expected 5 tasks')

    def test_tasks_filter_priority(self):
        self.connector.config['conflict_policy'] = 'sde'
        self.connector.config['sde_min_priority'] = 7
        self.connector.sde_connect()
        self.connector.alm_connect()

        # clear out default tasks
        self.mock_sde_response.clear_tasks()

        self.mock_sde_response.generate_sde_task(priority=8)
        self.mock_sde_response.generate_sde_task(priority=7)
        self.mock_sde_response.generate_sde_task(priority=7)
        self.mock_sde_response.generate_sde_task(priority=1)
        self.mock_sde_response.generate_sde_task(priority=6)

        tasks = self.connector.sde_get_tasks()
        self.assertTrue(len(tasks) == 3, 'Expected 3 tasks')

        for task in tasks:
            self.assertTrue(task['priority'] >= self.connector.config['sde_min_priority'],
                            'Task %s has an unexpected priority %d' % (task['id'], task['priority']))

    def test_tasks_filter_phase(self):
        self.connector.config['conflict_policy'] = 'sde'
        self.connector.config['sde_min_priority'] = 7
        self.connector.config['alm_phases'] = ['requirements', 'testing']
        self.connector.sde_connect()
        self.connector.alm_connect()

        # clear out default tasks
        self.mock_sde_response.clear_tasks()

        self.mock_sde_response.generate_sde_task(priority=7, phase='requirements')
        self.mock_sde_response.generate_sde_task(priority=7, phase='testing')
        self.mock_sde_response.generate_sde_task(priority=7, phase='development')

        tasks = self.connector.sde_get_tasks()
        self.assertTrue(len(tasks) == 3, 'Expected 3 tasks')

        tasks = self.connector.filter_tasks(tasks)
        self.assertTrue(len(tasks) == 2, 'Expected 2 tasks')

        for task in tasks:
            self.assertTrue(task['phase'] in self.config['alm_phases'],
                            'Task %s has unexpected phase %s' % (task['id'], task['phase']))

    def test_update_existing_task_sde(self):
        # The plugin may initialize variables during alm_connect() so we need
        # to call alm_connect() before proceeding
        self.connector.config['conflict_policy'] = 'sde'
        self.connector.config['alm_phases'] = ['requirements', 'testing', 'development']
        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.synchronize()
        alm_task = self.connector.alm_get_task(test_task)
        self.connector.alm_update_task_status(alm_task, 'DONE')

    def test_update_task_status_to_done(self):
        self.connector.config['conflict_policy'] = 'alm'
        self.connector.config['alm_phases'] = ['requirements', 'testing', 'development']
        self.connector.alm_connect()
        # Most of the module test configurations set the minimum priority to be 8
        # so we will create a task with this priority to make sure its in scope
        test_task = self.mock_sde_response.generate_sde_task(priority=8)
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'DONE',
                            'Cannot update task status to DONE because status is already DONE')

        self.connector.alm_update_task_status(alm_task, 'DONE')
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertEqual(test_task_result.get_status(), 'DONE', 'Failed to update task status to DONE')
        self.connector.synchronize()
        the_task = self.connector.sde_get_task(test_task['id'])
        self.assertEqual(the_task['status'], 'DONE', 'Failed to update SDE task to DONE')

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
        self.connector.alm_add_task(test_task)
        alm_task = self.connector.alm_get_task(test_task)

        self.assertNotEqual(alm_task.get_status(), 'TODO',
                            'Cannot update task status to TODO because status is already TODO')

        self.connector.alm_update_task_status(alm_task, 'TODO')
        test_task_result = self.connector.alm_get_task(test_task)

        self.assertEqual(test_task_result.get_status(), 'TODO', 'Failed to update task status to TODO')

    def test_remove_alm_task(self):
        if not self.connector.alm_supports_delete():
            return

        self.connector.alm_connect()
        test_task = self.mock_sde_response.generate_sde_task()
        self.connector.alm_add_task(test_task)
        test_task_result = self.connector.alm_get_task(test_task)
        self.assertNotNone(test_task_result, 'Task added to ALM')
        self.connector.alm_remove_task(test_task_result)
        test_task_result = self.connector.alm_get_task(test_task)

    def test_synchronize(self):
        # Verify no exceptions are thrown
        self.connector.synchronize()

    def test_api_exceptions_are_handled(self):
        # Check that all api exceptions are properly handled
        for api_target, mock_flag in self.response_generator.rest_api_targets.iteritems():
            self.tearDown()
            self.setUp()
            self.connector.config['conflict_policy'] = 'sde'
            self.connector.config['alm_phases'] = ['requirements', 'testing', 'development']
            self.mock_sde_response.get_response_generator().generator_clear_resources()
            # All response methods should throw an exception if the fail flag is encountered
            self.mock_alm_response.set_response_flags({mock_flag: 'fail'})

            try:
                # This will invoke add, get and update task
                self.connector.alm_connect()
                test_task = self.mock_sde_response.generate_sde_task()
                test_task['status'] = 'DONE'
                self.connector.alm_add_task(test_task)
                self.connector.synchronize()
                test_task = self.mock_sde_response.generate_sde_task(phase='testing')
                requirement_task = self.mock_sde_response.generate_sde_task(phase='requirements')
                self.assertNotNone(requirement_task, 'Expected requirements task to be generated')
                self.connector.synchronize()
                raise Exception('Expected an AlmException to be thrown for the following target: %s' % api_target)
            except AlmException:
                pass

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
