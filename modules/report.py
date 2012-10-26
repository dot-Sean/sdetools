# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Proof of concept of a report generator
# Piggybacks off Ehsan's Lint tool code

import csv
from sdelib.cmd import BaseCommand
from sdelib.interactive_plugin import PlugInExperience

CSV_FILENAME = "output.csv"

class Command(BaseCommand):
    help = 'Creates a CSV output of project details for reporting purposes (Proof of Concept only!)'

    def configure(self):
        self.plugin = PlugInExperience(self.config)

    def test_report(self, plugin):
         app_list = plugin.api.get_applications()

         csv_file = csv.writer(open(CSV_FILENAME, 'wb'))
         csv_file.writerow(['Application','Project','Task','Weakness','Status'])

         for app_ind in xrange(len(app_list)):
              app = app_list[app_ind]
              proj_list = plugin.api.get_projects(app['id'])

              for proj_ind in xrange(len(proj_list)):
                  proj = proj_list[proj_ind]
                  task_list = plugin.api.get_tasks(proj['id'])

                  for task_ind in xrange(len(task_list)):
                      task = task_list[task_ind]
                      csv_file.writerow([app['name'],proj['name'],task['title'],task['weakness']['title'],task['status']])

    def handle(self):
        self.test_report(self.plugin)
        return True
