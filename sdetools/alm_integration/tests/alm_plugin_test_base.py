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
        MOCK_SDE.patch_sde_mocks(path_to_alm_connector)
        ret_chn = ReturnChannel(stdout_callback, {})
        cls.config = Config('', '', ret_chn, 'import')

        cls.init_alm_connector()
        Config.parse_config_file(cls.config, conf_path)
        cls.tac.initialize()
        cls.init_response_generator()

    @abstractmethod
    def init_response_generator(self):
        pass

    @abstractmethod
    def init_alm_connector(self):
        pass

    def setUp(self):
        self.sde_tasks = None
        self.alm_tasks = None

    def tearDown(self):
        MOCK_RESPONSE.response_generator_clear_tasks()
        MOCK_RESPONSE.set_mock_flag({})

    def test_alm_configurations(self):
        configs = self.tac.config
        self.assertTrue(configs.get('sde_server'))
        self.assertTrue(configs.get('alm_server'))

    def test_alm_connect(self):
        self.tac.alm_connect()

    def test_add_task(self):
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        test_task_result = self.tac.alm_get_task(test_task)
        self.assertTrue(test_task_result.get_alm_id())
        self.assertTrue(test_task_result.get_status())

    def test_update_task_status_to_done(self):
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)
        self.tac.alm_update_task_status(alm_task, 'DONE')
        test_task_result = self.tac.alm_get_task(test_task)
        self.assertEqual(test_task_result.get_status(), 'DONE')

    def test_update_task_status_to_na(self):
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)
        self.tac.alm_update_task_status(alm_task,'NA')
        test_task_result = self.tac.alm_get_task(test_task)
        self.assertTrue((test_task_result.get_status() == 'DONE') or
                        (test_task_result.get_status() == 'NA'))

    def test_update_task_status_to_todo(self):
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)
        self.assertEqual(alm_task.get_status(), 'TODO')
        self.tac.alm_update_task_status(alm_task, 'DONE')
        new_alm_task = self.tac.alm_get_task(test_task)
        self.assertEqual(new_alm_task.get_status(), 'DONE')
        self.tac.alm_update_task_status(new_alm_task, 'TODO')
        test_task_result = self.tac.alm_get_task(test_task)
        self.assertEqual(test_task_result.get_status(), 'TODO')

    def test_synchronize(self):
        # TODO: This isn't really a test. We aren't verifying anything
        #       besides the fact it doesn't raise exceptions.
        self.tac.synchronize()

    def assert_exception(self, exception, error_code, reason, fn, *args):
        if not exception:
            raise AssertionError('No exception specified')
        if not fn:
            raise AssertionError('No function specified')
        if not exception and not error_code:
            raise AssertionError('No error code or error message to assert')

        try:
            fn.__call__(*args)
        except Error, err:
            print err.value
            self.assertEqual(type(err), exception, 'Expected exception type %s, Got %s' % (exception, type(err)))

            if error_code:
                self.assertEqual(err.code, error_code, 'Expected error code %s, Got %s' % (error_code, err.code))
            if reason:
                self.assertTrue(reason in err.value, "Expected error message '%s', Got '%s'" % (reason, err.value))
