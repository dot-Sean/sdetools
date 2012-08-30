# Copyright SDElements Inc
#
# Plugin for two way integration with JIRA

import sys, os
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from sdelib.conf_mgr import config
from sdelib.interactive_plugin import PlugInExperience

from jira_integration.lib.jira_plugin import JIRAConnector
from jira_integration.lib.jira_plugin import JIRABase, add_jira_config_options
from alm_integration.alm_plugin_base import AlmException
from sdelib.interactive_plugin import PluginError


def main(argv):
    try:
        add_jira_config_options(config)
        ret = config.parse_args(argv)
        
        if not ret:
            sys.exit(1)
        
        sde_plugin = PlugInExperience(config)
        jbase = JIRABase(config)    
        jira = JIRAConnector(sde_plugin, jbase)
        jira.synchronize()
    except (AlmException, PluginError) as e:
        print 'The following error was encountered: %s' % e
    
if __name__ == "__main__":
    main(sys.argv)
