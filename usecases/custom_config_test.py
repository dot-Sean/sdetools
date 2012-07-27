#!/usr/bin/python
#
# Version 0.5
# Ehsan Foroughi
# Copyright SDElements Inc
#

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdelib.conf_mgr import Config

def main(argv):
    config = Config()
    config.add_custom_option('mytest', 'This is my test option', 'm')

    ret = config.parse_args(argv)
    if not ret:
        sys.exit(1)
    
    print 'Tests you can do'
    print '1. Run with -h to see the options'
    print '2. Run with -m <value> to set the option'
    print '3. Add myvar = <value> to config file of your choice'
    print
    print 'RESULT: The value of mytest config is %s' % (config['mytest'])

if __name__ == "__main__":
    main(sys.argv)

