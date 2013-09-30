from sdetools.sdelib import conf_mgr
from sdetools.sdelib.mod_mgr import ReturnChannel

from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod

import sdetools.analysis_integration.tests.interactive_plugin

MOCK_PLUGIN = sdetools.analysis_integration.tests.interactive_plugin

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
        MOCK_PLUGIN.patch_plugin_experience()
        self.config = conf_mgr.Config(self.SDE_CMD, [], NullReturnChannel(null_callback), 'shell', {})

    def note_check(self, task_id, result, status):
        self.assertTrue(True)

    @abstractmethod
    def expected_number_of_findings(self):
        pass

    def test_import_findings(self):
        self.integrator.initialize()
        self.integrator.load_mapping_from_xml()
        self.integrator.parse()
        self.assertTrue(not self.config['trial_run'])
        task_list = self.integrator.plugin.get_task_list()
        total_nontest_tasks = len([task for task in task_list
                                   if task['phase'] not in ['testing']])
        self.integrator.load_mapping_from_xml()
        self.integrator.parse()
        findings = self.integrator.generate_findings()
        self.assertTrue(len(findings) == self.expected_number_of_findings())

        result = self.integrator.import_findings()
        self.assertTrue(result.error_count == 0)
        all_tasks_sanity_check = (len(result.noflaw_tasks) + len(result.affected_tasks)) == total_nontest_tasks
        self.assertTrue(all_tasks_sanity_check)
        self.assertTrue(result.error_weaknesses_unmapped == 0)

        for task_id in result.noflaw_tasks:
            self.note_check(task_id, result, "DONE")

        for task_id in result.affected_tasks:
            self.note_check(task_id, result, "TODO")
