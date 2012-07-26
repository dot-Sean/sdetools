#!/usr/bin/python
#
# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Proof of concept for extensible two way
# integration with ALM tools

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

import csv

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience
import logging

from alm_plugin_base import AlmConnector, AlmTask, AlmException

class TestAlmTask(AlmTask):
     """      Simple test ALM Task       """

     def __init__(self, task_id, alm_id, priority, status, timestamp):
          self.task_id = task_id
          self.alm_id = alm_id
          self.priority = priority
          self.status = status
          self.timestampe = timestamp
     
     def get_task_id(self):
          return self.task_id

     def get_alm_id(self):
          return self.alm_id
     
     def get_priority(self):
          return self.priority        
          
     def get_status(self):
          return self.status       

     def get_timestamp(self):
          return self.timestamp

     
class TestAlmConnector(AlmConnector):
    """ Test class. 'Connects' to a CSV file that has a list of tasks
    """
    def alm_name(self):
          return "CSV File"

    def alm_connect(self):
          self.fields = ['id','priority','status']
          #CHANGE CONFIGURATION TO self.sde_plugin['file'] 
          self.csv_file = open(self.configuration['file'], 'r+b')

    def alm_get_task (self, task):

          (alm_task, reader) = self.find_matching_row(task)
 
          if (alm_task):
               return TestAlmTask(alm_task['id'],
                                  '%d' % (reader.line_num),
                                  alm_task['priority'],
                                  alm_task['status'],
                                  None)
          return None

    def find_matching_row(self, task):
          reader = csv.DictReader(self.csv_file, self.fields)
          
          for row in reader:
               if (row['id'] == task['id']):
                    return (row, reader)

          return (None, reader)
          
    def alm_add_task(self, task):
          writer = csv.writer(self.csv_file, self.fields)
          writer.writerow(['%s' % task['id'], '%s' % task['priority'],
                           '%s' % task['status']])
          return None

    def alm_update_task_status(self, task, status):

          alm_task_row = self.find_matching_row(task)
 
          if (alm_task_row):
               writer = csv.DictWriter(self.csv_file, self.fields)
               writer[alm_task_row]['status'] = status
          

    def alm_disconnect(self):
          pass



def load():
     
    plugin = PlugInExperience(config)
    tac = TestAlmConnector(plugin, None, {'file':'test.csv',
                                          'phases':['requirements',
                                                    'development']})
    tac.synchronize()

def main(argv):
    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)

    load()

if __name__ == "__main__":
    main(sys.argv)

