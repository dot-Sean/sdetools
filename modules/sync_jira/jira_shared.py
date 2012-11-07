from alm_integration.alm_plugin_base import AlmTask

class JIRATask(AlmTask):
    """ Representation of a task in JIRA """

    def __init__(self, task_id, alm_id, priority, status, resolution,
                 timestamp, done_statuses):
        self.task_id = task_id
        self.alm_id = alm_id
        self.priority = priority
        self.status = status
        self.resolution = resolution
        self.timestamp = timestamp
        self.done_statuses = done_statuses  # comma-separated list

    def get_task_id(self):
        return self.task_id

    def get_alm_id(self):
        return self.alm_id

    def get_priority(self):
        return self.priority

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

    @classmethod
    def translate_priority(cls, priority):
        """ Translates an SDE priority into a JIRA priority """
        try:
            priority = int(priority)
        except (TypeError):
            logger.error('Could not coerce %s into an integer' % priority)
            raise AlmException("Error in translating SDE priority to JIRA: "
                               "%s is not an integer priority" % priority)
        if priority == 10:
            return 'Blocker'
        elif 7 <= priority <= 9:
            return 'Critical'
        elif 5 <= priority <= 6:
            return 'Major'
        elif 3 <= priority <= 4:
            return 'Minor'
        else:
            return 'Trivial'

