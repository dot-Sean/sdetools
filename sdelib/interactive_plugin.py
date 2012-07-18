import sys
import getpass

from commons import show_error
import apiclient
from content import Content

class PlugInExperience:
    def __init__(self, config):
        self.config = config
        self.api = apiclient.APIBase(self.config)
        self.connected = False

    def connect(self):
        if self.config['authmode'] == 'session':
            ret_err, ret_val = self.api.start_session()
        else:
            #TODO: Find a better alternative ->
            #In 'basic' mode, we make an extra call just to verify that credentials are correct
            ret_err, ret_val = self.api.get_applications()
        if not ret_err:
            self.connected = True
        return ret_err, ret_val

    def get_and_validate_password(self):
        while not self.connected:
            if self.config['askpasswd']:
                print "Enter the password for account: %s" % (self.config['username'])
                self.config.settings['password'] = getpass.getpass()
            ret_err, ret_val = self.connect()
            if not ret_err:
                break
            elif ret_err == 401:
                if self.config['askpasswd']:
                    print "Password Error\n"
                    continue
                show_error('Invalid Email/Password')
            elif ret_err == -1:
                show_error(ret_val)
            else:
                show_error('Unexpected Error - code %s: %s' % (ret_err, ret_val))
            sys.exit(1)

    def select_application(self):
        filters = {}
        if self.config['application']:
            filters['name'] = self.config['application']
        ret_err, ret_val = self.api.get_applications(**filters)
        if ret_err:
            return ret_err, ret_val
        app_list = ret_val

        if (self.config['application']):
            if (not app_list):
                return -1, 'Specified Application not found -> %s' % (self.config['application'])
            elif (len(app_list) == 1):
                return 0, app_list[0]

        if (not self.config['interactive']):
            return -1, 'Missing Application (either use Interactive mode, or specify the exact name of an Application)'

        if (not app_list):
            return -1, 'No Applications to choose from'

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

        return 0, sel_app

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
            ret_err, ret_val = self.select_application()
            if ret_err:
                return ret_err, ret_val
            sel_app = ret_val

            filters = {}
            if self.config['project']:
                filters['name'] = self.config['project']
            ret_err, ret_val = self.api.get_projects(sel_app['id'], **filters)
            if ret_err:
                return ret_err, ret_val
            prj_list = ret_val

            if (self.config['project']):
                if (not prj_list):
                    return -1, 'Specified Project not found -> %s' % (self.config['project'])
                elif (len(prj_list) == 1):
                    return 0, (sel_app, prj_list[0])

            if (not self.config['interactive']):
                return -1, 'Missing Project (either use Interactive mode, or specify the exact name of an Project)'

            sel_prj = self._select_project_from_list(prj_list)
            if sel_prj is not None:
                return 0, (sel_app, sel_prj)

    def get_task_list(self):
        ret_err, ret_val = self.select_project()
        if ret_err:
            return ret_err, ret_val
        self.app, self.prj = ret_val
        
        ret_err, ret_val = self.api.get_tasks(self.prj['id'])
        return ret_err, ret_val

    def get_compiled_task_list(self):
        if not self.connected:
            self.get_and_validate_password()

        ret_err, ret_val = self.get_task_list()
        if ret_err:
            return ret_err, ret_val
        task_list = ret_val

        content = Content(self.api)
        content.import_task_list(task_list)
        return 0, content

    def add_note(self, task_id, text, filename, status):
        if not self.connected:
            return -1, 'Not logged in'

        if (not self.prj['id']):
            return -1, 'Missing Project'

        return self.api.add_note("%d-%s" % (self.prj['id'], task_id), text, filename, status)

