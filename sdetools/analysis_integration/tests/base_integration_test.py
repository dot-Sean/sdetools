import os

from sdetools.sdelib import conf_mgr
from sdetools.sdelib.mod_mgr import ReturnChannel
from sdetools.sdelib.testlib.mock_response import MOCK_SDE_RESPONSE
from sdetools.sdelib.commons import abc, get_directory_of_current_module
abstractmethod = abc.abstractmethod
TEST_FILES_DIR = 'files'


def stdout_callback(obj):
    print obj


class BaseIntegrationTest(object):
    sde_cmd = ""
    integrator = None
    config = None

    @classmethod
    def setUpClass(cls, sde_cmd, mapping_file, report_file, integrator_cls, test_files_dir=TEST_FILES_DIR):
        cls.sde_cmd = sde_cmd
        cls.mapping_file = mapping_file
        cls.report_file = report_file
        cls.integrator_cls = integrator_cls
        cls.test_file_dir = os.path.join(get_directory_of_current_module(cls), test_files_dir)
        cls.mock_sde_response = MOCK_SDE_RESPONSE

    def setUp(self):
        ret_chn = ReturnChannel(stdout_callback, {})
        self.config = conf_mgr.Config(self.sde_cmd, [], ret_chn, 'shell', {})

        self.init_integrator()
        self.setup_sde_configs()
        self.mock_sde_response.initialize(self.config)
        self.integrator.load_mapping_from_xml()

    def init_data(self):
        self.integrator.initialize()
        self.integrator.parse()

    def setup_sde_configs(self):
        self.config['sde_server'] = 'sdelements.com'
        self.config['sde_application'] = 'Test App'
        self.config['sde_project'] = 'Test Project'
        self.config['trial_run'] = False
        self.config['flaws_only'] = False

    def tearDown(self):
        self.mock_sde_response.teardown()

    def init_integrator(self):
        self.integrator = self.integrator_cls(self.config)
        self.integrator.config['mapping_file'] = os.path.join(self.test_file_dir, self.mapping_file)
        self.integrator.config['report_file'] = os.path.join(self.test_file_dir, self.report_file)
        self.num_reports = 1

    def test_import_with_file_ext_wildcard(self):
        report_file = os.path.splitext(self.report_file)[0]
        report_file = os.path.join(self.test_file_dir, report_file) + '.*'
        self.integrator.config['report_file'] = report_file

        self.test_import_findings_assert_failed_tasks()

    def test_import_with_file_name_wildcard(self):
        report_file = os.path.splitext(self.report_file)[0]
        report_file = os.path.join(self.test_file_dir, report_file) + '*'
        self.integrator.config['report_file'] = report_file

        self.test_import_findings_assert_failed_tasks()

    def test_import_with_multiple_files(self):
        report_file = os.path.join(self.test_file_dir, self.report_file)
        self.integrator.config['report_file'] = '%s,%s' % (report_file, report_file)
        self.num_reports = 2

        self.test_import_findings_assert_failed_tasks()

    def check_analysis_note(self, task_id, expected_status, expected_confidence, expected_count):
        expected_count *= self.num_reports
        analysis_task_note = self.integrator.plugin.get_task_notes('T%s' % task_id)['analysis'][0]

        if expected_count:
            findings = analysis_task_note['findings'][0]
            self.assertEqual(findings['count'], expected_count, 'Expected %s count(s) of %s for task %s, got %s' %
                            (expected_count, findings['desc'], task_id, findings['count']))
        self.assertEqual(analysis_task_note['status'], expected_status, 'Expected analysis status for task %s to '
                         'be %s, got %s' % (task_id, expected_status, analysis_task_note['status']))
        self.assertEqual(analysis_task_note['confidence'], expected_confidence, 'Expected analysis confidence for task'
                         '%s to be %s, got %s' % (task_id, expected_confidence, analysis_task_note['confidence']))

    @abstractmethod
    def expected_number_of_findings(self):
        pass

    def test_expected_number_of_findings(self):
        self.init_data()
        findings = self.integrator.generate_findings()
        self.assertEqual(len(findings), self.expected_number_of_findings(), 'Expected %s findings, got %s' %
                        (self.expected_number_of_findings(), len(findings)))

    def test_all_tasks_sanity_check(self):
        self.init_data()
        task_list = self.integrator.plugin.get_task_list()
        total_nontest_tasks = len([task for task in task_list
                                   if task['phase'] not in ['testing']])
        result = self.integrator.import_findings()
        sum_of_tasks = len(result.noflaw_tasks) + len(result.affected_tasks)
        self.assertEqual(sum_of_tasks, total_nontest_tasks, 'Sum of unaffected and affected tasks does not match total'
                        'number of non-test tasks')

    def test_import_findings_assert_unmapped_tasks(self):
        self.init_data()
        result = self.integrator.import_findings()

        self.assertEqual(result.error_count, 0, 'Expected 0 errors, got %s' % result.error_count)

        self.assertEqual(result.error_weaknesses_unmapped, 1, 'Expected 1 unmapped weakness, got %s' %
                         result.error_weaknesses_unmapped)
        self.assertFalse('193' in result.noflaw_tasks, 'Task 193 is not suppose to be mapped to an unaffected task')
        self.assertFalse('193' in result.affected_tasks, 'Task 193 is not suppose to be mapped to an affected task')

    def test_import_findings_assert_passed_tasks(self):
        self.init_data()
        result = self.integrator.import_findings()

        self.assertEqual(len(result.noflaw_tasks), 2, 'Expected 2 unaffected tasks, got %s' % len(result.noflaw_tasks))
        self.assertTrue('40' in result.noflaw_tasks, 'Expected to find task 40 in unaffected tasks')
        self.check_analysis_note('40', 'partial', 'low', 0)
        self.assertTrue('38' in result.noflaw_tasks, 'Expected to find task 38 in unaffected tasks')
        self.check_analysis_note('38', 'partial', 'high', 0)

    def test_import_findings_assert_failed_tasks(self):
        self.init_data()
        result = self.integrator.import_findings()

        self.assertEqual(len(result.affected_tasks), 1, 'Expected 1 affected tasks, got %s' % len(result.affected_tasks))
        self.assertTrue('36' in result.affected_tasks, 'Expected to find task 36 in affected tasks')
        self.check_analysis_note('36', 'failed', 'high', 1)

