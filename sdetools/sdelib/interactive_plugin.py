from commons import Error, get_password
import sdeapi
from content import Content


def _verify_connect(wrapped):
    def wrapper(self, *args, **kwargs):
        if not self.connected:
            self.connect()
        if self.prj_id is None:
            self.app_id, self.prj_id = self.select_project()
        return wrapped(self, *args, **kwargs)

    return wrapper


class PluginError(Error):
    pass


class PlugInExperience:
    def __init__(self, config):
        self.config = config
        self.api = sdeapi.APIBase(self.config)
        self.app_id = None
        self.prj_id = None
        config.opts.add('sde_application', "SDE Application to use", default='', group_name="SD Elements Connector")
        config.opts.add('sde_project', "SDE Project to use", default='', group_name="SD Elements Connector")
        self.connected = False

    def connect(self):
        if self.connected:
            return

        if not self.api.connected:
            if self.config['interactive']:
                self.get_and_validate_password()
            else:
                self.api.connect()

        # We allow IDs to be passed when importing sdetools
        if type(self.config['sde_application']) in [int, long]:
            self.app_id = self.config['sde_application']
            if type(self.config['sde_project']) in [int, long]:
                self.prj_id = self.config['sde_project']

        self.connected = True

    def get_and_validate_password(self):
        askpasswd = self.config['sde_pass'] is None
        while not self.api.connected:
            if askpasswd:
                print "Enter the password for account: %s" % (self.config['email'])
                self.config['sde_pass'] = get_password()
            try:
                self.api.connect()
            except self.api.APIAuthError:
                if askpasswd:
                    print "Incorrect Email/Password\n"
                    continue
                raise
            break

    def select_application(self):
        if not self.connected:
            self.connect()

        filters = {}
        if self.config['sde_application']:
            filters['name'] = self.config['sde_application']
        app_list = self.api.get_applications(**filters)

        if self.config['sde_application']:
            if not app_list:
                raise PluginError('Specified Application not found -> %s' % (self.config['sde_application']))
            elif len(app_list) == 1:
                return app_list[0]['id']

        if not self.config['interactive']:
            raise PluginError('Missing Application (either use Interactive mode, or specify the exact name of an Application)')

        if not app_list:
            raise PluginError('No Applications to choose from')

        sel_app = None
        while sel_app is None:
            for app_ind in xrange(len(app_list)):
                app = app_list[app_ind]
                print "%2d. %s" % (app_ind+1, app['name'])
            while True:
                print
                print "Enter the Application number you want to select\n Tip: Enter empty to show the Application list again"
                sel_ind = raw_input()
                if not sel_ind:
                    break
                if (not sel_ind.isdigit()) or (int(sel_ind) <= 0) or (int(sel_ind) > len(app_list)):
                    print "Invalid entry, please try again"
                    continue
                sel_app = app_list[int(sel_ind)-1]
                break

        return sel_app['id']

    def _select_project_from_list(self, prj_list):
        while True:
            print " 0. <Select a different Application>"
            for prj_ind in xrange(len(prj_list)):
                prj = prj_list[prj_ind]
                print "%2d. %s" % (prj_ind+1, prj['name'])
            while True:
                print
                print "Enter the Project number you want to select\n Tip: Enter empty to show the Project list again, or Enter 0 to select a different Application"
                sel_ind = raw_input()
                if not sel_ind:
                    break
                if (not sel_ind.isdigit()) or (int(sel_ind) > len(prj_list)):
                    print "Invalid entry, please try again"
                    continue
                if sel_ind == '0':
                    return None
                return prj_list[int(sel_ind)-1]

    def select_project(self):
        while True:
            sel_app_id = self.select_application()

            filters = {}
            if self.config['sde_project']:
                filters['name'] = self.config['sde_project']
            prj_list = self.api.get_projects(sel_app_id, **filters)

            if self.config['sde_project']:
                if not prj_list:
                    raise PluginError('Specified Project not found -> %s' % (self.config['sde_project']))
                elif len(prj_list) == 1:
                    return sel_app_id, prj_list[0]['id']

            if not self.config['interactive']:
                raise PluginError('Missing Project (either use Interactive mode, or specify the exact name of an Project)')

            sel_prj = self._select_project_from_list(prj_list)
            if sel_prj is not None:
                return sel_app_id, sel_prj['id']

    def get_compiled_task_list(self):
        task_list = self.get_task_list()

        content = Content(self.api)
        content.import_task_list(task_list)
        return content

    @_verify_connect
    def get_task_list(self, options={}, **filters):
        return self.api.get_tasks(self.prj_id, options, **filters)

    @_verify_connect
    def add_task_ide_note(self, task_id, text, filename, status):
        return self.api.add_task_ide_note("%d-%s" % (self.prj_id, task_id), text, filename, status)

    @_verify_connect
    def update_task_ide_note(self, note_id, text, status=None):
        return self.api.update_task_ide_note(note_id, text, status)

    @_verify_connect
    def update_task_text_note(self, note_id, text):
        return self.api.update_task_text_note(note_id, text)

    @_verify_connect
    def get_task_notes(self, task_id, note_type=''):
        return self.api.get_task_notes("%d-%s" % (self.prj_id, task_id), note_type)

    @_verify_connect
    def add_project_analysis_note(self, analysis_ref, analysis_type):
        return self.api.add_project_analysis_note(self.prj_id, analysis_ref, analysis_type)

    @_verify_connect
    def add_analysis_note(self, task_id, analysis_ref, confidence, findings, behaviour, task_status_mapping=None):
        return self.api.add_analysis_note("%d-%s" % (self.prj_id, task_id),
                                          analysis_ref, confidence, findings, behaviour, task_status_mapping)

    @_verify_connect
    def get_taskstatuses(self):
        return self.api.get_taskstatuses()

    @_verify_connect
    def get_phases(self):
        return self.api.get_phases()