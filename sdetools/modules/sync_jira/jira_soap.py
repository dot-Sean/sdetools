import xml.parsers.expat
import socket
import urllib2

from sdetools.extlib import SOAPpy
from sdetools.extlib import http_req

from sdetools.alm_integration.alm_plugin_base import AlmException
from sdetools.modules.sync_jira.jira_shared import JIRATask

from sdetools.sdelib import log_mgr
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
            except (xml.parsers.expat.ExpatError, socket.error):
                raise AlmException('Unable to access JIRA (for %s). '
                        ' Please check network connectivity.' % (self.__fname))

    def __init__(self, proxy):
        self.proxy = proxy

    def __getattr__(self, name):
        f = getattr(self.proxy, name)
        return self.__FCall(f, name)

class JIRASoapAPI:
    def __init__(self, config):
        self.config = config
        self.statuses = None
        self.priorities = None
        self.auth = None
        self.versions = None

    def connect_server(self):
        config = SOAPpy.Config
        if __name__ in self.config['debug_mods']:
            config.debug = 1

        opener = http_req.get_opener(self.config['alm_method'], self.config['alm_server'])
        self.config['alm_server'] = opener.server

        try:
            stream = opener.open('%s://%s/rpc/soap/jirasoapservice-v2?wsdl' %
                    (self.config['alm_method'], self.config['alm_server']))
        except urllib2.URLError, err:
            raise AlmException('Unable to reach JIRA service (Check URL). Reason: %s' % (err))
        except http_req.InvalidCertificateException, err:
            raise AlmException('Unable to verify SSL certificate for host: %s' % (self.config['alm_server']))

        # Get a proxy to the server
        try:
            proxy = SOAPpy.WSDL.Proxy(stream, config=config)
        except (SOAPpy.Types.faultType, xml.parsers.expat.ExpatError), err:
            raise AlmException('Error talking to JIRA service. Please check server URL. Reason: %s' % (err))
        self.proxy = SOAPProxyWrap(proxy)

        # Attempt to login
        try:
            self.auth = self.proxy.login(self.config['alm_user'], self.config['alm_pass'])
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to login to JIRA. Please check ID, password')

        # For JIRA 4 we need the ID-Name mapping for status and priority
        self.statuses = self.proxy.getStatuses(self.auth)
        self.priorities = self.proxy.getPriorities(self.auth)

    def connect_project(self):
        # Test for project existence
        try:
            # We don't use the result of this call
            self.proxy.getProjectByKey(self.auth, self.config['alm_project'])
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to connect to project %s. Please check project'
                               ' settings' % (self.config['alm_project']))
        
        self.versions = self.proxy.getVersions(self.auth, self.config['alm_project'])

    def get_issue_types(self):
        try:
            return self.proxy.getIssueTypes(self.auth)
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to get issuetypes from JIRA')

    def get_subtask_issue_types(self):
        try:
            return self.proxy.getSubTaskIssueTypes(self.auth)
        except SOAPpy.Types.faultType:
            raise AlmException('Unable to get subtask issuetypes from JIRA')

    def get_task(self, task, task_id):
        try:
            jql = "project='%s' AND summary~'%s\\\\:'" % (self.config['alm_project'], task_id)
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
        task_versions = []

        if hasattr(jtask, 'resolution') and jtask.resolution:
            task_resolution = jtask.resolution
        if jtask.status:
            for status in self.statuses:
                if status['id'] == jtask.status:
                    task_status = status['name']
                    break
        if hasattr(jtask, 'priority'):
            for priority in self.priorities:
                if priority['id'] == jtask.priority:
                    task_priority = priority['name']
                    break
        if hasattr(jtask, 'affectsVersions') and jtask.affectsVersions:
            for version in jtask.affectsVersions:
                task_versions.append(version['name'])

        return JIRATask(task_id,
                        jtask['key'],
                        task_priority,
                        task_status,
                        task_resolution,
                        jtask['updated'],
                        self.config['jira_done_statuses'],
                        task_versions)

    def get_version(self, version_name):
        for v in self.versions:
            if v['name']==version_name:
                return v
        return None
         
    def setup_fields(self, jira_issue_type_id):

        self.custom_fields = []
        self.fields = []

        create_fields = []

        # We use self.proxy.getFieldsForCreate to determine which fields are applicable to issues to avoid
        # sending fields which have been removed from a project, for instance 'priority'. Unfortunately, this method 
        # was only exposed in Jira 4.4. We assuming all fields are fair game for versions prior to 4.4
        if hasattr(self.proxy, 'getFieldsForCreate'):
            try:
                create_fields = self.proxy.getFieldsForCreate(self.auth, self.config['alm_project'], 
                                                              SOAPpy.Types.longType(long(jira_issue_type_id)))
            except SOAPpy.Types.faultType, fault:
                raise AlmException('Could not retrieve fields for JIRA project %s: %s' % (self.config['alm_project'], 
                                   fault))

        if create_fields:
            for f in create_fields:
                self.fields.append({'name':f['name'], 'id':f['id']})

        if self.config['alm_custom_fields'] and self.config['jira_existing_issue']:
            try:
                issue_fields = self.proxy.getFieldsForEdit(self.auth, self.config['jira_existing_issue'])
            except SOAPpy.Types.faultType, fault:
                raise AlmException('Could not retrieve custom fields for JIRA issue %s: %s' % 
                                   (self.config['jira_existing_issue'], fault))

            for key in self.config['alm_custom_fields']:
                for field in issue_fields:
                    if (key == field['name']):
                        self.custom_fields.append({'field': field['id'],'value':self.config['alm_custom_fields'][key]})

            if len(self.custom_fields) != len(self.config['alm_custom_fields']):
                raise AlmException('At least one custom field could not be found')            

    def has_field(self, field_name):
        # We assume all fields are fair game for Jira versions prior to 4.4 (see comment in 'setup_fields' above)
        if not self.fields:
             return True
             
        for field in self.fields:
            if (field_name == field['id']):
                return True
                
        return False
                
    def get_affected_versions(self, task):
        affected_versions = []
        for version_name in task.versions:
            jira_version = self.get_version(version_name)
            if jira_version:
                affected_versions.append(jira_version['id'])
            else:
                raise AlmException("Version %s could not be found in JIRA. '\
                        'Check your sync settings or add the version to JIRA" % version_name)
        return affected_versions

    def set_version(self, task, project_version):
        update = [{'id':'versions', 'values':self.get_affected_versions(task)}]
        try:
            self.proxy.updateIssue(self.auth, task.get_alm_id(), update)
        except (SOAPpy.Types.faultType, AlmException):
            raise AlmException('Unable to update issue %s with new version %s' % (task.get_alm_id(), project_version))
    
        return True

    def add_task(self, task, issue_type_id, project_version):
        #Add task
        selected_priority = None
        for priority in self.priorities:
            if priority['name'] == task['alm_priority']:
                selected_priority = priority['id']
                break
        if not selected_priority:
            raise AlmException('Unable to find priority %s' % task['alm_priority'])

        updates = []
        updates.append({'id':'labels', 'values':['SD-Elements']})
                
        if project_version:
            updates.append({'id':'versions', 'values':[project_version['id']]})
        args = {
            'project': self.config['alm_project'],
            'summary': task['title'],
            'description': task['formatted_content'],
            'type': issue_type_id
        }

        if self.has_field('priority'):
            args['priority'] = selected_priority

        if self.custom_fields:
            arg_custom_fields = []
            for custom_field in self.custom_fields:
                arg_custom_fields.append({'customfieldId':custom_field['field'],'values':[custom_field['value']]})
            args['customFieldValues'] = arg_custom_fields
        try:
            if self.config['alm_parent_issue']:
                ref = self.proxy.createIssueWithParent(self.auth, args, self.config['alm_parent_issue'])
            else:
                ref = self.proxy.createIssue(self.auth, args)
            self.proxy.updateIssue(self.auth, ref['key'], updates)
        except SOAPpy.Types.faultType, err:
            raise AlmException('Unable to add issue to JIRA. Reason: %s' % (err.faultstring))
        return ref

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
            
    def post_conf_init(self):
        pass

