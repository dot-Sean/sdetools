#!/usr/bin/python
#
# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Proof of concept for extensible two way
# integration with JIRA

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience

from jira_plugin import JIRATask, JIRAConnector, JIRAConfig, JIRABase 
import logging


def main(argv):

    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)
    jira_config = JIRAConfig()
    jira_config.set_settings({
              ###### JIRA settings  ######
              ######General settings######
              #Server name, includes port
              #(e.g. example.atlassian.net:8080)
              'server':'sdetest.atlassian.net',
              
              #Username for JIRA user that can:
              # -create new issues for the project
              # -read existing issues in the project
              # -create transitions on issues (e.g. close an issue)
              'username':'sdetest',
              
              #Password for above user. Note that this will be encrypted
              #in future versions of the plugin
              'password':'YZC9H6etExRj2KNLeUjTNZU3jR',              
              
              ######Project settings######
              #JIRA project key
              'project':'TESTG',
              
              #JIRA allows workflow customization. Customized workflows
              #may make it difficult for the plugin to close a ticket
              #in JIRA. Thus, if the workflow is non-standard then
              #the plugin will not create transitions on issues
              #Valid values: True, False
              'standard_workflow' : True,

              #issue type for new issues raised by SD Elements
              'issue_id' : '1',

              #tranisition id for a closed ticket in JIRA
              'close_transition' : '2',

              #transition id for a re-opened ticket in JIRA
              'reopen_transition' : '3',

              #SD Elements task phases that are in scope.
              #Valid values: comma separated list-
              #['requirements,'architecture-design',
              # 'development','testing']
              'phases':['requirements'],

              #Which system takes precedence in case of
              #confliciting status. For example, if you mark
              #an issue as Closed in JIRA and the task is TODO in
              #SD Elements, it will be changed to DONE in SD Elemenets.
              #If you mark a task as Done in SD Elements, but it's still
              #Open in JIRA, the task will automatically revert back
              #to TODO in SD Elements.
              #Valid values:
              #'alm' -> ALM tool (i.e JIRA) takes precedence
              #'sde' -> SDE takes precedence
              #Note that timezone is currently unsupported
              #since JIRA does not provide timezone support
              'conflict_policy':'alm',


              ######Base settings, do not modify######
              'method':'https',
              'targets': None,
              'debug_level': 0,
              'skip_hidden': True,
              'interactive': True,
              'askpasswd': False,
              'auth_mode': 'basic',
              'application': None,
              })
    
    
    jbase = JIRABase(jira_config)
    sde_plugin = PlugInExperience(config)
    jira = JIRAConnector(sde_plugin, jbase, jira_config)
    jira.synchronize()
              
    
if __name__ == "__main__":
    main(sys.argv)
