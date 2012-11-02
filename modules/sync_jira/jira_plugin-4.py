# Copyright SDElements Inc
# Extensible two way integration with JIRA

from datetime import datetime

import xml.parsers.expat
import socket

from extlib import SOAPpy 
from sdelib.restclient import RESTBase, APIError
from alm_integration.alm_plugin_base import AlmTask, AlmConnector
from alm_integration.alm_plugin_base import AlmException
from sdelib.conf_mgr import Config

from sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class JIRAAPIBase(RESTBase):
    """ Base plugin for JIRA """

    def __init__(self, config):
        super(JIRAAPIBase, self).__init__('alm', 'JIRA', config, 'rest/api/2')

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

class JIRAConnector(AlmConnector):

    def __init__(self, config, alm_plugin):
        """ Initializes connection to JIRA """
        super(JIRAConnector, self).__init__(config, alm_plugin)

        config.add_custom_option('alm_standard_workflow', 'Standard workflow in JIRA?',
                default='True')
        config.add_custom_option('jira_issue_type', 'IDs for issues raised in JIRA',
                default='Bug')
        config.add_custom_option('jira_close_transition', 'Close transition in JIRA',
                default='Close Issue')
        config.add_custom_option('jira_reopen_transition', 'Re-open transiiton in JIRA',
                default='Reopen Issue')
        config.add_custom_option('jira_done_statuses', 'Statuses that signify a task is Done in JIRA',
                default='Resolved,Closed')

    def initialize(self):
        super(JIRAConnector, self).initialize()

        #Verify that the configuration options are set properly
        if (not self.sde_plugin.config['jira_done_statuses'] or
            len(self.sde_plugin.config['jira_done_statuses']) < 1):
            raise AlmException('Missing jira_done_statuses in configuration')

        self.sde_plugin.config['jira_done_statuses'] = (
                self.sde_plugin.config['jira_done_statuses'].split(','))

        if not self.sde_plugin.config['alm_standard_workflow']:
            raise AlmException('Missing alm_standard_workflow in configuration')
        if not self.sde_plugin.config['jira_issue_type']:
            raise AlmException('Missing jira_issue_type in configuration')
        if not self.sde_plugin.config['jira_close_transition']:
            raise AlmException('Missing jira_close_transition in configuration')
        if not self.sde_plugin.config['jira_reopen_transition']:
            raise AlmException('Missing jira_reopen_transition in configuration')

        self.close_transition_id = None
        self.reopen_transition_id = None
        self.jira_issue_type_id = None
        self.priorities = None
        self.statuses = None
        self.priorities = None
        self.auth = None
        self.jira = None
        
    def alm_name(self):
        return "JIRA"

    def alm_connect(self):

        # Get a proxy to the server
        try:
            self.jira = SOAPpy.WSDL.Proxy('%s://%s/rpc/soap/jirasoapservice-v2?wsdl' %
                                      (self.sde_plugin.config['alm_method'], self.sde_plugin.config['alm_server']))
        except (SOAPpy.Types.faultType, xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)
            raise AlmException('Unable to connect to JIRA. Please check server URL')
        except (xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)            
            raise AlmException('Unable to connect to JIRA. Please' +
                               ' check network connectivity' )

        # Attempt to login
        try:
            self.auth = self.jira.login(self.sde_plugin.config['alm_user'], self.sde_plugin.config['alm_pass'])
        except (SOAPpy.Types.faultType) as err:
            logger.warn(err)            
            raise AlmException('Unable to login to JIRA. Please check ID, password')
        except (xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)            
            raise AlmException('Unable to login to JIRA. Please check network connectivity')

        # Test for project existence
        try:
            result = self.jira.getProjectByKey(self.auth, self.sde_plugin.config['alm_project'])
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException('Unable to connect to project %s. Please' +
                               ' check project settings' % (self.sde_plugin.config['alm_project']))
        except (xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)            
            raise AlmException('Unable to connect to project %s. Please' +
                               ' check network connectivity' % (self.sde_plugin.config['alm_project']))
        
        #get Issue ID for given type name
        try:
            issue_types = self.jira.getIssueTypes(self.auth)
            for issue_type in issue_types:
                if (issue_type['name'] ==
                        self.sde_plugin.config['jira_issue_type']):
                    self.jira_issue_type_id = issue_type['id']
                    break
            if not self.jira_issue_type_id:
                raise AlmException('Issue type %s not available' %
                                   self.sde_plugin.config['jira_issue_type'])
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException('Unable to get issuetype from JIRA')
        except (xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)            
            raise AlmException('Unable to get issuetype from JIRA. Please check network connectivity')
        
        self.statuses = self.jira.getStatuses(self.auth)
        self.priorities = self.jira.getPriorities(self.auth)
        
    def alm_get_task (self, task):
        task_id = task['title'].partition(':')[0]
        result = None
        try:
            jql = "project='%s' AND summary~'%s'" % (
                    self.sde_plugin.config['alm_project'], task_id)
            issues = self.jira.getIssuesFromJqlSearch( self.auth, jql, SOAPpy.Types.intType(1) )
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException("Unable to get task %s from JIRA" % task_id)
        except (xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)
            raise AlmException("Unable to get task %s from JIRA. Please check network connectivity" % task_id)
            
        if not issues or len(issues) <= 0:
            #No result was found from query
            return None
        #We will use the first result from the query
        jtask = issues[0]

        task_resolution = None
        task_status = None
        task_priority = None

        if jtask['resolution']:
            task_resolution = jtask['resolution']
        if jtask['status']:
            for status in self.statuses:
                if status['id'] == jtask['status']:
                    task_status = status['name']
                    break
        if jtask['priority']:
            for priority in self.priorities:
                if priority['id'] == jtask['priority']:
                    task_priority = priority['name']
                    break

        return JIRATask(task['id'],
                        jtask['key'],
                        task_priority,
                        task_status,
                        task_resolution,
                        jtask['updated'],
                        self.sde_plugin.config['jira_done_statuses'])

    def alm_add_task(self, task):

        selected_priority = None
        for priority in self.priorities:
            if priority['name'] == JIRATask.translate_priority(task['priority']):
                selected_priority = priority['id']
                break
        if not selected_priority:
            raise AlmException('Unable to find priority %s' %
                                                JIRATask.translate_priority(task['priority']))        
        #Add task
        add_result = None
        args= {
               'project': self.sde_plugin.config['alm_project'],
               'summary':task['title'],
               'description':task['content'],
               'priority':selected_priority,
               'type': self.jira_issue_type_id
               }

        try:
            new_issue = self.jira.createIssue(self.auth,args)
        except (SOAPpy.Types.faultType, xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)
            return None

        if (self.sde_plugin.config['alm_standard_workflow'] == 'True' and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(self.alm_get_task(task), task['status'])

        #Return a unique identifier to this task in JIRA
        return 'Issue %s' % new_issue['key']

    def alm_update_task_status(self, task, status):
        if (not task or
            not self.sde_plugin.config['alm_standard_workflow'] == 'True'):
            return
        trans_result = None
        transitions = self.jira.getAvailableActions(self.auth, task.get_alm_id())
        # TODO: these two block are nearly identical: refactor
        try:
            if status == 'DONE' or status == 'NA':
                if not self.close_transition_id:
                    for transition in transitions:
                        if transition['name'] == self.sde_plugin.config['jira_close_transition']:
                            self.close_transition_id = transition['id']
                            break
                    if not self.close_transition_id:
                        raise AlmException('Unable to find transition %s' %
                                self.sde_plugin.config['jira_close_transition'])
                trans_result = self.jira.progressWorkflowAction(self.auth,task.get_alm_id(),self.close_transition_id)
            elif status=='TODO':
                #We are updating a closed task to TODO
                if not self.reopen_transition_id:
                    for transition in transitions:
                        if transition['name'] == self.sde_plugin.config['jira_reopen_transition']:
                            self.reopen_transition_id = transition['id']
                            break
                    if not self.reopen_transition_id:
                        raise AlmException('Unable to find transition %s' %
                                self.sde_plugin.config['jira_reopen_transition'])

                trans_result = self.jira.progressWorkflowAction(self.auth,task.get_alm_id(),self.reopen_transition_id)                
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException("Unable to set task status: %s" % err)
        except (xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)
            raise AlmException("Unable to set task status: %s. Check network connectivity" % err)
        

    def alm_disconnect(self):
        pass
