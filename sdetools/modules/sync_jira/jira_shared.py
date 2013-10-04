import datetime
from sdetools.alm_integration.alm_plugin_base import AlmTask

class JIRATask(AlmTask):
    """ Representation of a task in JIRA """

    def __init__(self, task_id, alm_id, priority, status, resolution,
                 timestamp, done_statuses, versions):
        self.task_id = task_id
        self.alm_id = alm_id
        self.status = status

        self.priority = priority
        self.resolution = resolution
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list
        self.versions = versions # array of version names

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_status(self):
        """ Translates JIRA priority into SDE priority """
        if self.status in self.done_statuses:
            return 'DONE'
        else:
            return 'TODO'

    def get_timestamp(self):
        """ Returns a datetime object """
        return datetime.strptime(self.timestamp.split('.')[0],
                                 '%Y-%m-%dT%H:%M:%S')

