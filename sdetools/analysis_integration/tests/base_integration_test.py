from sdetools.sdelib import conf_mgr
from sdetools.sdelib.mod_mgr import ReturnChannel

from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod

import sdetools.alm_integration.tests.alm_mock_response
from sdetools.sdelib.testlib.sde_response_generator import SdeResponseGenerator
MOCK_RESPONSE = sdetools.alm_integration.tests.alm_mock_response

def null_callback(obj):
    pass

class NullReturnChannel(ReturnChannel):
    def __init__(self, call_back, call_back_args={}):
        super(NullReturnChannel, self).__init__(call_back, call_back_args)

    def set_info_container(self, info_cls):
        pass

    def emit_obj(self, obj):
        pass

    def emit_it(self, *args, **kwargs):
        pass

    def queue(self, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def emit_info(self, *args, **kwargs):
        pass

    def emit_error(self, *args, **kwargs):
        pass

class BaseIntegrationTest(object):
    SDE_CMD = ""
    integrator = None
    config = None

    def setUp(self):
        self.config = conf_mgr.Config(self.SDE_CMD, [], NullReturnChannel(null_callback), 'shell', {})

        self.init_integrator()
        self.config['sde_api_token'] = 'apiToken123@sdelements.com'
        self.config['sde_application'] = 'Test App'
        self.config['sde_project'] = 'Test Project'
        self.config['trial_run'] = False
        self.config['flaws_only'] = False
        mock_path = 'sdetools.sdelib.sdeapi.restclient'
        response_generator = SdeResponseGenerator(self.config['sde_api_token'].split('a')[1],
                                                  self.config['sde_application'],
                                                  self.config['sde_project'],
                                                  self.config['sde_method'])

        MOCK_RESPONSE.patch_call_rest_api(response_generator, mock_path)

        self.integrator.initialize()
        self.integrator.load_mapping_from_xml()
        self.integrator.parse()

    def tearDown(self):
        MOCK_RESPONSE.response_generator_clear_tasks()
        MOCK_RESPONSE.set_response_flags({})

    @abstractmethod
    def init_integrator(self):
        pass

    def note_check(self, task_id, result, status):
        analysis_task_notes = self.integrator.plugin.get_task_notes('T%s' % task_id)['analysis']
        print analysis_task_notes
    def check_analysis_note(self, task_id, expected_status, expected_confidence):
        analysis_task_notes = self.integrator.plugin.get_task_notes('T%s' % task_id)['analysis']
        self.assertEqual(analysis_task_notes[0]['status'], expected_status)
        self.assertEqual(analysis_task_notes[0]['confidence'], expected_confidence)

    @abstractmethod
    def expected_number_of_findings(self):
        pass

    def test_expected_number_of_findings(self):
        findings = self.integrator.generate_findings()
        self.assertEqual(len(findings), self.expected_number_of_findings())

    def test_all_tasks_sanity_check(self):
        task_list = self.integrator.plugin.get_task_list()
        total_nontest_tasks = len([task for task in task_list
                                   if task['phase'] not in ['testing']])
        result = self.integrator.import_findings()

        self.assertTrue((len(result.noflaw_tasks) + len(result.affected_tasks)) == total_nontest_tasks)

    def test_import_findings_assert_unmapped_tasks(self):
        result = self.integrator.import_findings()

        self.assertEqual(result.error_count, 0)

        self.assertEqual(result.error_weaknesses_unmapped, 1)
        self.assertFalse('193' in result.noflaw_tasks)
        self.assertFalse('193' in result.affected_tasks)

    def test_import_findings_assert_passed_tasks(self):
        result = self.integrator.import_findings()

        self.assertEqual(len(result.noflaw_tasks), 1)
        self.assertTrue('40' in result.noflaw_tasks)
        self.check_analysis_note('40', 'partial', 'low')

    def test_import_findings_assert_failed_tasks(self):
        result = self.integrator.import_findings()

        self.assertEqual(len(result.affected_tasks), 2)
        self.assertTrue('38' in result.affected_tasks)
        self.check_analysis_note('38', 'failed', 'high')
        self.assertTrue('36' in result.affected_tasks)
        self.check_analysis_note('36', 'failed', 'low')

