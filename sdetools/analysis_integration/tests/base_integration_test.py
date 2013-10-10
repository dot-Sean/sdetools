from sdetools.sdelib import conf_mgr
from sdetools.sdelib.mod_mgr import ReturnChannel
from sdetools.sdelib.testlib.alm_mock_response import MOCK_SDE_RESPONSE
from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod


def stdout_callback(obj):
    print obj


class BaseIntegrationTest(object):
    SDE_CMD = ""
    integrator = None
    config = None

    @classmethod
    def setUpClass(cls):
        cls.mock_sde_response = MOCK_SDE_RESPONSE

    def setUp(self):
        ret_chn = ReturnChannel(stdout_callback, {})
        self.config = conf_mgr.Config(self.SDE_CMD, [], ret_chn, 'shell', {})

        self.init_integrator()
        self.config['sde_api_token'] = 'apiToken123@sdelements.com'
        self.config['sde_application'] = 'Test App'
        self.config['sde_project'] = 'Test Project'
        self.config['trial_run'] = False
        self.config['flaws_only'] = False

        self.mock_sde_response.initialize(self.config)
        self.integrator.initialize()
        self.integrator.load_mapping_from_xml()
        self.integrator.parse()

    def tearDown(self):
        self.mock_sde_response.teardown()

    @abstractmethod
    def init_integrator(self):
        pass

    def check_analysis_note(self, task_id, expected_status, expected_confidence):
        analysis_task_note = self.integrator.plugin.get_task_notes('T%s' % task_id)['analysis'][0]
        self.assertEqual(analysis_task_note['status'], expected_status, 'Expeceted analysis status for task %s to '
                'be %s, got %s' % (task_id, expected_status, analysis_task_note['status']))
        self.assertEqual(analysis_task_note['confidence'], expected_confidence, 'Expeceted analysis confidence for task'
                '%s to be %s, got %s' % (task_id, expected_confidence, analysis_task_note['confidence']))

    @abstractmethod
    def expected_number_of_findings(self):
        pass

    def test_expected_number_of_findings(self):
        findings = self.integrator.generate_findings()
        self.assertEqual(len(findings), self.expected_number_of_findings(), 'Expected %s findings, got %s' %
                (self.expected_number_of_findings(), len(findings)))

    def test_all_tasks_sanity_check(self):
        task_list = self.integrator.plugin.get_task_list()
        total_nontest_tasks = len([task for task in task_list
                                   if task['phase'] not in ['testing']])
        result = self.integrator.import_findings()
        sum_of_tasks = len(result.noflaw_tasks) + len(result.affected_tasks)
        self.assertEqual(sum_of_tasks, total_nontest_tasks, 'Sum of unaffected and affected tasks does not match total'
                'number of non-test tasks')

    def test_import_findings_assert_unmapped_tasks(self):
        result = self.integrator.import_findings()

        self.assertEqual(result.error_count, 0, 'Expected 0 errors, got %s' % result.error_count)

        self.assertEqual(result.error_weaknesses_unmapped, 1, 'Expected 1 unmapped weakness, got %s' %
                  result.error_weaknesses_unmapped)
        self.assertFalse('193' in result.noflaw_tasks, 'Task 193 is not suppose to be mapped to an unaffected task')
        self.assertFalse('193' in result.affected_tasks, 'Task 193 is not suppose to be mapped to an affected task')

    def test_import_findings_assert_passed_tasks(self):
        result = self.integrator.import_findings()

        self.assertEqual(len(result.noflaw_tasks), 2, 'Expected 2 unaffected tasks, got %s' % len(result.noflaw_tasks))
        self.assertTrue('40' in result.noflaw_tasks, 'Expected to find task 40 in unaffected tasks')
        self.check_analysis_note('40', 'partial', 'low')
        self.assertTrue('38' in result.noflaw_tasks, 'Expected to find task 38 in unaffected tasks')
        self.check_analysis_note('38', 'partial', 'high')

    def test_import_findings_assert_failed_tasks(self):
        result = self.integrator.import_findings()

        self.assertEqual(len(result.affected_tasks), 1, 'Expected 1 affected tasks, got %s' % len(result.affected_tasks))
        self.assertTrue('36' in result.affected_tasks, 'Expected to find task 36 in affected tasks')
        self.check_analysis_note('36', 'failed', 'high')

