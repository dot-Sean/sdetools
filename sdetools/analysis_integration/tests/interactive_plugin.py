from mock import patch

PLUGIN_CLASS = 'sdetools.sdelib.interactive_plugin.PlugInExperience'


def patch_plugin_experience():
    patch('%s.connect' % PLUGIN_CLASS, patch_plugin_experience_connect).start()
    patch('%s.get_and_validate_password' % PLUGIN_CLASS, patch_plugin_experience_get_and_validate_password).start()
    patch('%s.select_application' % PLUGIN_CLASS, patch_plugin_experience_select_application).start()
    patch('%s._select_project_from_list' % PLUGIN_CLASS, patch_plugin_experience__select_project_from_list).start()
    patch('%s.select_project' % PLUGIN_CLASS, patch_plugin_experience_select_project).start()
    patch('%s.get_compiled_task_list' % PLUGIN_CLASS, patch_plugin_experience_get_compiled_task_list).start()
    patch('%s.get_task_list' % PLUGIN_CLASS, patch_plugin_experience_get_task_list).start()
    patch('%s.add_task_ide_note' % PLUGIN_CLASS, patch_plugin_experience_add_task_ide_note).start()
    patch('%s.get_task_notes' % PLUGIN_CLASS, patch_plugin_experience_get_task_notes).start()
    patch('%s.add_project_analysis_note' % PLUGIN_CLASS, patch_plugin_experience_add_project_analysis_note).start()

def patch_plugin_experience_connect(self):
    pass

def patch_plugin_experience_get_and_validate_password(self):
    pass

def patch_plugin_experience_select_application(self):
    pass

def patch_plugin_experience__select_project_from_list(prj_list):
    pass

def patch_plugin_experience_select_project(self):
    pass

def patch_plugin_experience_get_compiled_task_list(self):
    pass

def patch_plugin_experience_get_task_list(self):
    return []

def patch_plugin_experience_add_task_ide_note(self,task_id, text, filename, status):
    pass

def patch_plugin_experience_get_task_notes(self,task_id, note_type=''):
    pass

def patch_plugin_experience_add_project_analysis_note(self,analysis_ref, analysis_type):
    return {'id': 1}

def patch_plugin_experience_add_analysis_note(self,task_id, analysis_ref, confidence, findings):
    pass

