import urllib
import urllib2
import base64

from sdelib.restclient import RESTBase
from xml.dom import minidom
import logging
logger = logging.getLogger(__name__)

class MingleAPIBase(RESTBase):
    def __init__(self, config):
        super(APIBase, self).__init__('alm', 'Mingle', config, 'api/v2/projects/%s' % config['alm_project'])

    def parse_response(self, result) 
        if result:
            try:
                result = minidom.parseString(result)
            except Exception, err:
                # This means that the result doesn't have XML, not an error
                pass
        return result

    def parse_response(self, result):
        encoded_args = dict((key.encode('utf-8'), val.encode('utf-8')) for key, val in args.items())
        return urllib.urlencode(encoded_args)
