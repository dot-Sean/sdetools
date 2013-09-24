import urllib, os, json
from sdetools.sdelib.commons import abc
abstractmethod = abc.abstractmethod


class TwoWayDict(dict):
    def __len__(self):
        return dict.__len__(self) / 2

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)


class AlmResponseGenerator(object):
    ALM_TASKS = TwoWayDict()

    def __init__(self, initial_task_status, test_dir):
        self.initial_task_status = initial_task_status
        self.test_dir = test_dir

    @abstractmethod
    def get_response(self, target, flag, data, method):
        pass

    def add_alm_task(self, task_name, id):
        if not self.ALM_TASKS.get(task_name):
            self.ALM_TASKS[task_name] = id
            self.ALM_TASKS['%s:status' % task_name] = self.initial_task_status
    
    def get_alm_task(self, key):
        return self.ALM_TASKS.get(key)

    def update_alm_task(self, key, value):
        if self.get_alm_task(key):
            self.ALM_TASKS[key] = value

    def clear_alm_tasks(self):
        self.ALM_TASKS = TwoWayDict()
	
    def urlencode_str(self, instr):
        return urllib.urlencode({'a':instr})[2:]
        
    def get_json_from_file(self, file_name):
        return json.loads(open('%s\\response\\%s.json' % (self.test_dir, file_name)).read())
