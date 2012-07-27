#!/usr/bin/python
#
# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Proof of concept of a report generator
# Piggybacks off Ehsan's Lint tool code

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

import csv

from sdelib.conf_mgr import config
from sdelib.commons import show_error, json
from sdelib.interactive_plugin import PlugInExperience

CSV_FILENAME = "output.csv"

def test_report(plugin):
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
              

def load():
    plugin = PlugInExperience(config)
    test_report(plugin)
    
def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    load()

if __name__ == "__main__":
    main(sys.argv)

