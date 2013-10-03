import os
import json
import re

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

    def add_alm_task(self, task_number):
        """
            Save task using the task number as the id
        """
        if not self.alm_tasks.get(task_number):
            self.alm_tasks[task_number] = {
                "name": "T%s" % task_number,
                "id": task_number,
                "status": self.initial_task_status,
            }

    def get_alm_task(self, task_number):
        return self.alm_tasks.get(task_number)

    def update_alm_task(self, task_number, field, value):
        if self.alm_tasks.get(task_number):
            self.alm_tasks[task_number][field] = value

    def clear_alm_tasks(self):
        self.alm_tasks = {}

    def get_json_from_file(self, obj_name):
        file_name = '%s.json' % (obj_name)
        file_path = os.path.join(self.test_dir, 'response', file_name)
        f = open(file_path)
        raw_json = f.read()
        f.close()

        return json.loads(raw_json)

    def get_task_number_from_title(self, s):
        task_number = re.search("(?<=T)[0-9]+((?=[:'])|$)", s)

        if task_number:
            return  task_number.group(0)
        else:
            return None
