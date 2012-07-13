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
from sdelib.commons import show_error
from sdelib.interactive_plugin import PlugInExperience
from sdelib.apiclient import json

CSV_FILENAME = "output.csv"

def test_report(plugin):
     ret_err, ret_val = plugin.api.get_applications()
     if ret_err:
         return ret_err, ret_val

     csv_file = csv.writer(open(CSV_FILENAME, 'wb'))
     csv_file.writerow(['Application','Project','Task','Weakness','Status'])
     app_list = ret_val

     for app_ind in xrange(len(app_list)):
          app = app_list[app_ind]
          proj_ret_err, proj_ret_val = plugin.api.get_projects(app['id'])
          if proj_ret_err:
              return proj_ret_err, proj_ret_val

          proj_list = proj_ret_val
          for proj_ind in xrange(len(proj_list)):
              proj = proj_list[proj_ind]
              task_ret_err, task_ret_val = plugin.api.get_tasks(proj['id'])
              if task_ret_err:
                  return task_ret_err, task_ret_val

              task_list = task_ret_val
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

