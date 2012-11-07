import xml.parsers.expat
import socket

from extlib import SOAPpy 

from alm_integration.alm_plugin_base import AlmException

class SOAPProxyWrap:
    """
    This is a wrapper for proxy calls so that we don't repeat the exception handling code everywhere
    """
    class __FCall:
        def __init__(self, fobj, fname):
            self.__fobj = fobj
            self.__fname = fname

        def __call__(self, *args):
            try:
                return self.__fobj(*args)
            except (xml.parsers.expat.ExpatError, socket.error), err:
                logger.error(err)            
                raise AlmException('Unable to access JIRA (for %s). '
                        ' Please check network connectivity.' % (self.fname))

    def __init__(self, proxy):
        self.proxy = proxy

    def __getattr__(self, name):
        f = getattr(self.proxy, name)
        return __FCall(f, proxy, name)

class JIRASoapAPI:
    def __init__(self, config):
        self.config = config

    def initialize(self):
        self.statuses = None
        self.priorities = None
        self.auth = None
        
    def connect(self):
        # Get a proxy to the server
        try:
            self.proxy = SOAPpy.WSDL.Proxy('%s://%s/rpc/soap/jirasoapservice-v2?wsdl' %
                    (self.config['alm_method'], self.config['alm_server']))
        except (SOAPpy.Types.faultType, xml.parsers.expat.ExpatError, socket.error) as err:
            logger.error(err)
            raise AlmException('Unable to connect to JIRA. Please check server URL')

        # Attempt to login
        try:
            self.auth = self.proxy.login(self.config['alm_user'], self.config['alm_pass'])
        except (SOAPpy.Types.faultType) as err:
            logger.warn(err)            
            raise AlmException('Unable to login to JIRA. Please check ID, password')

        # Test for project existence
        try:
            result = self.proxy.getProjectByKey(self.auth, self.config['alm_project'])
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException('Unable to connect to project %s. Please' +
                               ' check project settings' % (self.config['alm_project']))
       
        #get Issue ID for given type name
        try:
            issue_types = self.proxy.getIssueTypes(self.auth)
            for issue_type in issue_types:
                if (issue_type['name'] ==
                        self.config['jira_issue_type']):
                    self.jira_issue_type_id = issue_type['id']
                    break
            if not self.jira_issue_type_id:
                raise AlmException('Issue type %s not available' % self.config['jira_issue_type'])
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException('Unable to get issuetype from JIRA')
        
        self.statuses = self.proxy.getStatuses(self.auth)
        self.priorities = self.proxy.getPriorities(self.auth)
        
    def alm_get_task (self, task):
        task_id = task['title'].partition(':')[0]
        result = None
        try:
            jql = "project='%s' AND summary~'%s'" % (self.config['alm_project'], task_id)
            issues = self.proxy.getIssuesFromJqlSearch(self.auth, jql, SOAPpy.Types.intType(1))
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException("Unable to get task %s from JIRA" % task_id)
            
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
                        self.config['jira_done_statuses'])

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
               'project': self.config['alm_project'],
               'summary':task['title'],
               'description':task['content'],
               'priority':selected_priority,
               'type': self.jira_issue_type_id
               }

        try:
            new_issue = self.proxy.createIssue(self.auth,args)
        except (SOAPpy.Types.faultType, AlmException) as err:
            logger.error(err)
            return None

        if (self.config['alm_standard_workflow'] == 'True' and
            (task['status'] == 'DONE' or task['status'] == 'NA')):
            self.alm_update_task_status(self.alm_get_task(task), task['status'])

        #Return a unique identifier to this task in JIRA
        return 'Issue %s' % new_issue['key']

    def alm_update_task_status(self, task, status):
        if (not task or
            not self.config['alm_standard_workflow'] == 'True'):
            return
        trans_result = None
        transitions = self.proxy.getAvailableActions(self.auth, task.get_alm_id())
        # TODO: these two block are nearly identical: refactor
        try:
            if status == 'DONE' or status == 'NA':
                if not self.close_transition_id:
                    for transition in transitions:
                        if transition['name'] == self.config['jira_close_transition']:
                            self.close_transition_id = transition['id']
                            break
                    if not self.close_transition_id:
                        raise AlmException('Unable to find transition %s' %
                                self.config['jira_close_transition'])
                trans_result = self.proxy.progressWorkflowAction(self.auth,task.get_alm_id(), self.close_transition_id)
            elif status=='TODO':
                #We are updating a closed task to TODO
                if not self.reopen_transition_id:
                    for transition in transitions:
                        if transition['name'] == self.config['jira_reopen_transition']:
                            self.reopen_transition_id = transition['id']
                            break
                    if not self.reopen_transition_id:
                        raise AlmException('Unable to find transition %s' % self.config['jira_reopen_transition'])

                trans_result = self.proxy.progressWorkflowAction(self.auth, task.get_alm_id(), self.reopen_transition_id)                
        except (SOAPpy.Types.faultType) as err:
            logger.error(err)
            raise AlmException("Unable to set task status: %s" % err)
