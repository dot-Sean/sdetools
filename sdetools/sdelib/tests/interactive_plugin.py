from mock import patch

PLUGIN_CLASS = 'sdetools.sdelib.interactive_plugin'


class MockPlugInExperience(object):
    def __init__(self):
        self.api = None
        self.connected = True
        patch('%s.connect' % PLUGIN_CLASS, MockPlugInExperience.connect).start()
        patch('%s.get_and_validate_password' % PLUGIN_CLASS, MockPlugInExperience.get_and_validate_password).start()
        patch('%s.select_application' % PLUGIN_CLASS, MockPlugInExperience.select_application).start()
        patch('%s._select_project_from_list' % PLUGIN_CLASS, MockPlugInExperience._select_project_from_list).start()
        patch('%s.select_project' % PLUGIN_CLASS, MockPlugInExperience.select_project).start()
        patch('%s.get_compiled_task_list' % PLUGIN_CLASS, MockPlugInExperience.get_compiled_task_list).start()
        patch('%s.get_task_list' % PLUGIN_CLASS, MockPlugInExperience.get_task_list).start()
        patch('%s.add_task_ide_note' % PLUGIN_CLASS, MockPlugInExperience.add_task_ide_note).start()
        patch('%s.get_task_notes' % PLUGIN_CLASS, MockPlugInExperience.get_task_notes).start()
        patch('%s.add_project_analysis_note' % PLUGIN_CLASS, MockPlugInExperience.add_project_analysis_note).start()

    def connect(self):
        pass

    def get_and_validate_password(self):
        pass

    def select_application(self):
        pass

    def _select_project_from_list(self, prj_list):
        pass

    def select_project(self):
        pass

    def get_compiled_task_list(self):
        pass

    def get_task_list(self):
        pass

    def add_task_ide_note(self, task_id, text, filename, status):
        pass

    def get_task_notes(self, task_id, note_type=''):
        pass

    def add_project_analysis_note(self, analysis_ref, analysis_type):
        pass

    def add_analysis_note(self, task_id, analysis_ref, confidence, findings):
        pass
