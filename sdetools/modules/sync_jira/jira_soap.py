import xml.parsers.expat
import socket

from extlib import SOAPpy

from alm_integration.alm_plugin_base import AlmException
from modules.sync_jira.jira_shared import JIRATask

from sdelib import log_mgr
logger = log_mgr.mods.add_mod(__name__)

class SOAPProxyWrap:
    """
    This is a wrapper for proxy calls so that we don't repeat the exception handling code everywhere
    """
    class __FCall:
        def __init__(self, fobj, fname):
            self.__fobj = fobj
            self.__fname = fname

        def __call__(self, *args):
            logger.info('Calling JIRA SOAP method %s' % self.__fname)
            logger.debug(' + Args: %s' % ((repr(args)[:200]) + (repr(args)[200:] and '...')))
            try:
                return self.__fobj(*args)
            except (xml.parsers.expat.ExpatError, socket.error), err:
                raise AlmException('Unable to access JIRA (for %s). '
                        ' Please check network connectivity.' % (self.fname))

    def __init__(self, proxy):
        self.proxy = proxy

    def __getattr__(self, name):
        f = getattr(self.proxy, name)
        return self.__FCall(f, name)

class JIRASoapAPI:
    def __init__(self, config):
        self.config = config

    def initialize(self):
        self.statuses = None
        self.priorities = None
        self.auth = None
        
    def connect(self):
        config = SOAPpy.Config
        if __name__ in self.config['debug_mods']:
            config.debug = 1

        # Get a proxy to the server
        try:
            proxy = SOAPpy.WSDL.Proxy('%s://%s/rpc/soap/jirasoapservice-v2?wsdl' %
                    (self.config['alm_method'], self.config['alm_server']), config=config)
        except (SOAPpy.Types.faultType, xml.parsers.expat.ExpatError, socket.error), err:
            raise AlmException('Unable to connect to JIRA. Please check server URL')
        self.proxy = SOAPProxyWrap(proxy)

        # Attempt to login
        try:
            self.auth = self.proxy.login(self.config['alm_user'], self.config['alm_pass'])
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to login to JIRA. Please check ID, password')

        # Test for project existence
        try:
            result = self.proxy.getProjectByKey(self.auth, self.config['alm_project'])
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to connect to project %s. Please check project'
                               ' settings' % (self.config['alm_project']))
        
        # For JIRA 4 we need the ID-Name mapping for status and priority
        self.statuses = self.proxy.getStatuses(self.auth)
        self.priorities = self.proxy.getPriorities(self.auth)

    def get_issue_types(self):
        try:
            return self.proxy.getIssueTypes(self.auth)
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to get issuetype from JIRA')

    def get_task(self, task, task_id):
        try:
            jql = "project='%s' AND summary~'%s'" % (self.config['alm_project'], task_id)
            issues = self.proxy.getIssuesFromJqlSearch(self.auth, jql, SOAPpy.Types.intType(1))
        except SOAPpy.Types.faultType:
            raise AlmException("Unable to get task %s from JIRA" % task_id)

        # We can't simplify this since issues is a complex object
        if not issues or len(issues) == 0:
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

    def add_task(self, task, issue_type_id):
        #Add task
        selected_priority = None
        for priority in self.priorities:
            if priority['name'] == JIRATask.translate_priority(task['priority']):
                selected_priority = priority['id']
                break
        if not selected_priority:
            raise AlmException('Unable to find priority %s' %
                    JIRATask.translate_priority(task['priority']))        

        args = {
            'project': self.config['alm_project'],
            'summary': task['title'],
            'description': task['formatted_content'],
            'priority': selected_priority,
            'type': issue_type_id
        }

        try:
            return self.proxy.createIssue(self.auth, args)
        except (SOAPpy.Types.faultType, AlmException), err:
            raise AlmException('Unable to add issue to JIRA')

    def get_available_transitions(self, task_id):
        transitions = self.proxy.getAvailableActions(self.auth, task_id)
        ret_trans = {}
        for transition in transitions:
            ret_trans[transition['name']] = transition['id']
        return ret_trans

    def update_task_status(self, task_id, status_id):
        try:
            self.proxy.progressWorkflowAction(self.auth, task_id, status_id)                
        except SOAPpy.Types.faultType, err:
            logger.error(err)
            raise AlmException("Unable to set task status: %s" % err)
