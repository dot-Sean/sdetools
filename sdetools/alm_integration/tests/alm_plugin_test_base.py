from mock import patch

from sdetools.sdelib.mod_mgr import ReturnChannel
from sdetools.sdelib.conf_mgr import Config

import sdetools.alm_integration.tests.alm_mock_sde_plugin
MOCK_SDE = sdetools.alm_integration.tests.alm_mock_sde_plugin


def stdout_callback(obj):
    print obj


class AlmPluginTestBase(object):
    @classmethod
    def initTest(cls, PATH_TO_ALM_CONNECTOR):
        patch('%s.AlmConnector.sde_connect' % PATH_TO_ALM_CONNECTOR, MOCK_SDE.mock_sde_connect).start()
        patch('%s.AlmConnector.is_sde_connected' % PATH_TO_ALM_CONNECTOR, MOCK_SDE.mock_is_sde_connected).start()
        patch('%s.AlmConnector.sde_get_tasks' % PATH_TO_ALM_CONNECTOR, MOCK_SDE.mock_sde_get_tasks).start()
        patch('%s.AlmConnector.sde_get_task' % PATH_TO_ALM_CONNECTOR, MOCK_SDE.mock_sde_get_task).start()
        patch('%s.AlmConnector.sde_update_task_status' % PATH_TO_ALM_CONNECTOR, MOCK_SDE.mock_sde_update_task_status).start()
        patch('%s.AlmConnector.sde_get_task_content' % PATH_TO_ALM_CONNECTOR, MOCK_SDE.mock_sde_get_task_content).start()
        patch('%s.AlmConnector._add_note' % PATH_TO_ALM_CONNECTOR, MOCK_SDE.mock_add_note).start()
        ret_chn = ReturnChannel(stdout_callback, {})
        cls.config = Config('', '', ret_chn, 'import')
        return

    def setUp(self):
        self.sde_tasks = None
        self.alm_tasks = None

    def tearDown(self):
        pass

    def base_test_01_alm_configurations(self):
        configs = self.tac.config
        self.assertTrue(configs.get('sde_server'))
        self.assertTrue(configs.get('alm_server'))

    def base_test_02_alm_connect(self):
        self.tac.alm_connect()

    def base_test_03_get_task(self):
        self.sde_tasks = self.tac.sde_get_tasks()
        self.assertTrue(self.sde_tasks)
        #Check to see that all of the expected fields are there
        for task in self.sde_tasks:
            self.assertTrue(task.has_key('status'))
            self.assertTrue(task.has_key('timestamp'))
            self.assertTrue(task.has_key('phase'))
            self.assertTrue(task.has_key('id'))
            self.assertTrue(task.has_key('priority'))
            self.assertTrue(task.has_key('note_count'))

    def base_test_04_add_task(self):
        self.tac.alm_connect()
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        test_task_result = self.tac.alm_get_task(test_task)
        self.assertTrue(test_task_result)

    def base_test_05_update_task_status(self):
        self.tac.alm_connect()
        # Case 1: Create a task and update the status to DONE
        test_task = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task)
        alm_task = self.tac.alm_get_task(test_task)
        self.tac.alm_update_task_status(alm_task,'DONE')
        test_task_result = self.tac.alm_get_task(test_task)
        self.assertTrue(test_task_result)
        self.assertTrue(test_task_result.get_status() == 'DONE')
        # Case 2: Create a task and update the status to NA
        test_task2 = MOCK_SDE.generate_sde_task()
        self.tac.alm_add_task(test_task2)
        alm_task2 = self.tac.alm_get_task(test_task2)
        self.tac.alm_update_task_status(alm_task2,'NA')
        test_task2_result = self.tac.alm_get_task(test_task2)
        self.assertTrue((test_task2_result.get_status() == 'DONE') or
                        (test_task2_result.get_status() == 'NA'))
        # Case 3: Update the status of the task created in Case 2
        #         back to TODO
        alm_task2 = test_task2_result
        self.tac.alm_update_task_status(alm_task2,'TODO')
        test_task2_result = self.tac.alm_get_task(test_task2)
        self.assertTrue(test_task2_result.get_status() == 'TODO')

    def base_test_06_synchronize(self):
        # TODO: This isn't really a test. We aren't verifying anything
        #       besides the fact it doesn't raise exceptions.
        self.tac.synchronize()
