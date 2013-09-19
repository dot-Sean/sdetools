#NOTE: Before runngin ensure that the options are set
#properly in the configuration file

import sys, os, unittest
sys.path.append(os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0])

import csv

from sdetools.sdelib.conf_mgr import Config
from sdetools.sdelib.interactive_plugin import PlugInExperience
import logging

from sdetools.alm_integration.alm_plugin_base import AlmConnector, AlmTask


CONF_FILE_LOCATION = 'test_settings.conf'

class TestAlmTask(AlmTask):
    """ Simple test ALM Task """

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
    """ Example AlmConnector.

    'Connects' to a CSV file that has a list of tasks.
    """
    alm_name = 'CSV File'

    def alm_connect(self):
        self.fields = ['id', 'priority', 'status']
        self.csv_file = open('test.csv', 'r+b')

    def alm_get_task(self, task):
        alm_task, reader = self.find_matching_row(task)
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
        if alm_task_row:
            writer = csv.DictWriter(self.csv_file, self.fields)
            writer[alm_task_row]['status'] = status

    def alm_disconnect(self):
        pass

class TestALMCase(unittest.TestCase):
    def setUp(self):
        config.parse_config_file(CONF_FILE_LOCATION)
        self.plugin = PlugInExperience(config)
        self.tac = TestAlmConnector(self.plugin, None)
        self.sde_tasks = None
        self.alm_tasks = None

    def test_connect(self):
        """Tests that we can connect to SD Elements """
        self.assertNotEqual(self.tac, None)
        self.tac.sde_connect()
        self.assertTrue(self.tac.is_sde_connected())

    def test_sde_get_tasks(self):
        """Tests that we can get all tasks"""
        self.sde_tasks = self.tac.sde_get_tasks()
        self.assertTrue(self.sde_tasks)
        for task in self.sde_tasks:
            self.assertTrue(task.has_key('status'))
            self.assertTrue(task.has_key('timestamp'))
            self.assertTrue(task.has_key('phase'))
            self.assertTrue(task.has_key('id'))
            self.assertTrue(task.has_key('priority'))
            self.assertTrue(task.has_key('note_count'))

    def _get_changed_status(self, status):
        """ Returns a changed status from the one given """
        if status == 'TODO':
            return 'NA'
        elif status == 'DONE':
            return 'TODO'
        else:
            return 'DONE'

    def test_sde_update_task_status(self):
        """Tests that update status works on SD Elements"""
        self.sde_tasks = self.tac.sde_get_tasks()
        self.alm_tasks = []
        for i, task in enumerate(self.sde_tasks):
            almTask = TestAlmTask(task['id'],
                                  'TEST_ALM_%d' % i,
                                  task['priority'],
                                  task['status'],
                                  task['timestamp'])
            self.alm_tasks.append(almTask)
            logging.info("Testing to change status from" +
                         " %s to %s for %s" % (
                              task['status'],
                              self._get_changed_status(task['status']),
                              task['id']))

            self.tac.sde_update_task_status(task,
                    self._get_changed_status(task['status']))

            updated_task = self.tac.sde_get_task(task['id'])
            #Check to see that a note was successfully added to
            #indicate task status change
            self.assertEquals(updated_task['note_count'],
                              task['note_count'] + 1)

    def test_scoping(self):
        """Tests that we are only accepting the right kind of tasks"""
        self.sde_tasks = self.tac.sde_get_tasks()
        old_phases= self.tac.sde_plugin.config['alm_phases']
        self.tac.sde_plugin.config['alm_phases'] = ['made_up_phase']
        self.assertFalse(self.tac.in_scope(self.sde_tasks[0]))
        self.tac.sde_plugin.config['alm_phases'].append(self.sde_tasks[0]['phase'])
        self.assertTrue(self.tac.in_scope(self.sde_tasks[0]))
        self.tac.sde_plugin.config['alm_phases'] = old_phases

    def test_synchronize(self):
        """ Tests if full-fledged synchronization worked """
        # TODO: This doesn't actually verify anything worked, just that
        #       the command runs without exceptions.
        self.tac.synchronize()

if __name__ == "__main__":
    unittest.main()
