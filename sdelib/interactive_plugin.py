from commons import Error, get_password
import apiclient
from content import Content

class PluginError(Error):
    pass

class PlugInExperience:
    def __init__(self, config):
        self.config = config
        self.api = apiclient.APIBase(self.config)
        self.connected = False

    def connect(self):
        if self.config['authmode'] == 'session':
            result = self.api.start_session()
        else:
            #TODO: Find a better alternative ->
            #In 'basic' mode, we make an extra call just to verify that credentials are correct
            result = self.api.get_applications()
        self.connected = True
        return result

    def get_and_validate_password(self):
        askpasswd = (self.config['sde_pass'] is None)
        while not self.connected:
            if askpasswd:
                print "Enter the password for account: %s" % (self.config['email'])
                self.config['sde_passw'] = get_password()
            try:
                self.connect()
            except self.api.APIAuthError:
                if askpasswd:
                    print "Incorrect Email/Passwrd\n"
                    continue
                raise
            break

    def select_application(self):
        filters = {}
        if self.config['application']:
            filters['name'] = self.config['application']
        app_list = self.api.get_applications(**filters)

        if (self.config['application']):
            if (not app_list):
                raise PluginError('Specified Application not found -> %s' % (self.config['application']))
            elif (len(app_list) == 1):
                return app_list[0]

        if (not self.config['interactive']):
            raise PluginError('Missing Application (either use Interactive mode, or specify the exact name of an Application)')

        if (not app_list):
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

        return sel_app

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
            sel_app = self.select_application()

            filters = {}
            if self.config['project']:
                filters['name'] = self.config['project']
            prj_list = self.api.get_projects(sel_app['id'], **filters)

            if (self.config['project']):
                if (not prj_list):
                    raise PluginError('Specified Project not found -> %s' % (self.config['project']))
                elif (len(prj_list) == 1):
                    return (sel_app, prj_list[0])

            if (not self.config['interactive']):
                raise PluginError('Missing Project (either use Interactive mode, or specify the exact name of an Project)')

            sel_prj = self._select_project_from_list(prj_list)
            if sel_prj is not None:
                return (sel_app, sel_prj)

    def get_task_list(self):
        if not self.connected:
            self.get_and_validate_password()

        self.app, self.prj = self.select_project()
        
        return self.api.get_tasks(self.prj['id'])

    def get_compiled_task_list(self):
        task_list = self.get_task_list()

        content = Content(self.api)
        content.import_task_list(task_list)
        return content

    def add_note(self, task_id, text, filename, status):
        if not self.connected:
             self.get_and_validate_password()
 
        self.app, self.prj = self.select_project()

        return self.api.add_note("%d-%s" % (self.prj['id'], task_id), text, filename, status)

    def get_notes(self, task_id):
        if not self.connected:
             self.get_and_validate_password()

        self.app, self.prj = self.select_project()
 
        return self.api.get_notes("%d-%s" % (self.prj['id'], task_id))       
