import json
import re

from sdetools.extlib.defusedxml import minidom
from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod


class AlmResponseGenerator(object):
    def __init__(self, initial_task_status, test_dir):
        self.initial_task_status = initial_task_status
        self.test_dir = test_dir
        self.alm_tasks = {}

    @abstractmethod
    def get_response(self, target, flag, data, method):
        pass

    def add_alm_task(self, task_number, task_name=None, status=None):
        """
            Save task using the task number as the id
        """
        if not self.alm_tasks.get(task_number):
            if not task_name:
                task_name = "T%s" % task_number
            if not status:
                status = self.initial_task_status

            self.alm_tasks[task_number] = {
                "name": task_name,
                "id": task_number,
                "status": status
            }

    def get_alm_task(self, task_number):
        return self.alm_tasks.get(task_number)

    def update_alm_task(self, task_number, field, value):
        if self.alm_tasks.get(task_number):
            self.alm_tasks[task_number][field] = value

    def clear_alm_tasks(self):
        self.alm_tasks = {}

    def _read_response_file(self, file_name):
        file_path = '%s\\response\\%s' % (self.test_dir, file_name)
        f = open(file_path)
        return f.read()

    def get_json_from_file(self, file_name):
        raw_json = self._read_response_file('%s.json' % file_name)
        return json.loads(raw_json)

    def get_xml_from_file(self, file_name):
        raw_xml = self._read_response_file('%s.xml' % file_name)
        return minidom.parseString(raw_xml)

    def get_task_number_from_title(self, s):
        task_number = re.search("(?<=T)[0-9]+((?=[:'])|$)", s)

        if task_number:
            return  task_number.group(0)
        else:
            return None
