from sdelib.cmd import BaseCommand
from sdelib.apiclient import APIBase

class Command(BaseCommand):
    name = 'list_projects'
    help = 'Creates a list of applications and projects that contain a certain word in their name'\
        ' (Proof of Concept only!)'
    conf_syntax = '[search_string]'
    conf_help = 'search_string: [optional] The string to search the name of projects against.\n'\
        '  Use empty to list all'

    def configure(self):
        self.api = APIBase(self.config)

    def handle(self):
        search_str = ' '.join(self.args)

        app_list = self.api.get_applications()

        for app in app_list:
            app_output = False
            prj_list = self.api.get_projects(app['id'])
            for prj in prj_list:
                if search_str in prj['name']:
                    if not app_output:
                        app_output = True
                        print 'App %s: %s' % (app['id'], app['name'])
                    print '  Prj %s: %s' % (prj['id'], prj['name'])
        return True
