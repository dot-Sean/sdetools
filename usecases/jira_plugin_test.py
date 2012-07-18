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
    jira_config.set_settings({'method':'https', 'server':'sdetest.atlassian.net',
              'username':'sdetest', 'password':'YZC9H6etExRj2KNLeUjTNZU3jR',
              'project':'TESTG',
              'targets': None,
              'debug_level': 0,
              'skip_hidden': True,
              'interactive': True,
              'askpasswd': False,
              'auth_mode': 'basic',
              'application': None,
              'standard_workflow' : True,
              'phases':['requirements']})
    #Valid values for phases are 'requirements,'architecture-design',
    #'development','testing'
    
    jbase = JIRABase(jira_config)
    sde_plugin = PlugInExperience(config)
    jira = JIRAConnector(sde_plugin, jbase, jira_config)
    jira.synchronize()
              
    
if __name__ == "__main__":
    main(sys.argv)
