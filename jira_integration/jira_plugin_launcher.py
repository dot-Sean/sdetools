#!/usr/bin/python
#
# Version 0.01
# Rohit Sethi
# Copyright SDElements Inc
#
# Plugin for two way integration with JIRA

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience

from jira_plugin import JIRATask, JIRAConnector, JIRAConfig, JIRABase, add_jira_config_options

import logging
#import ConfigParser


def main(argv):

    add_jira_config_options(config)
    ret = config.parse_args(argv)
    
    if not ret:
        sys.exit(1)
    
    sde_plugin = PlugInExperience(config)
    jbase = JIRABase(config)    
    jira = JIRAConnector(sde_plugin, jbase)
    jira.synchronize()          
    
if __name__ == "__main__":
    main(sys.argv)
