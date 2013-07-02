# Version 0.01
# Copyright SDElements Inc


import csv
import datetime
from sdetools.sdelib.cmd import BaseCommand
from sdetools.sdelib.interactive_plugin import PlugInExperience

CSV_FILENAME = "output.csv"

class Command(BaseCommand):
    help = 'Creates a CSV output of project details for reporting purposes (Proof of Concept only!)'

    def configure(self):
        self.plugin = PlugInExperience(self.config)

        self.config.add_custom_option("list_archived", "Include Archived Projects (True|False)", 
            default="False")
        self.config.add_custom_option("created_after", "Project Created After (YYYY-MM-DD)", 
            default="9999-12-31")
        self.config.add_custom_option("created_before", "Project Created Before (YYYY-MM-DD)", 
            default="1900-01-01")


    def test_report(self, plugin):
        self.config.process_boolean_config('list_archived')
        self.config.process_date_config('created_after')
        self.config.process_date_config('created_before')

        app_list = plugin.api.get_applications()

        csv_file = csv.writer(open(CSV_FILENAME, 'wb'))
        csv_file.writerow(['Application','Project','Task','Weakness','Status'])

        for app_ind in xrange(len(app_list)):
             app = app_list[app_ind]
             proj_list = plugin.api.get_projects(app['id'])

             for proj_ind in xrange(len(proj_list)):
                 proj = proj_list[proj_ind]
                 import pdb
                 pdb.set_trace()
                 task_list = plugin.api.get_tasks(proj['id'])

                 for task_ind in xrange(len(task_list)):
                     task = task_list[task_ind]
                     csv_file.writerow([app['name'],proj['name'],task['title'],task['weakness']['title'],task['status']])

    def handle(self):
        self.test_report(self.plugin)
        return True
