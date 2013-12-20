# Copyright SDElements Inc

import ssl
import socket
from sdetools.sdelib.commons import UsageError, Error
from sdetools.sdelib.cmd import BaseCommand
from sdetools.extlib import http_req

SSL_END_MARKER = '-----END CERTIFICATE-----'

class Command(BaseCommand):
    help = 'Import a self-signed or other SSL certificate to sdetools'

    def configure(self):
        self.config.opts.add('server', "Server to connect to", 
            default=None)
        self.config.opts.add('port', "Port to connect to", 
            default='443')

    def handle(self):
        try:
            self.config['port'] = int(self.config['port'])
        except ValueError:
            raise UsageError('Port number invalid')
        try:
            cert = ssl.get_server_certificate((self.config['server'], self.config['port']))
        except ssl.SSLError, err:
            raise Error('Can not establish SSL connection with the specified server/port.'
                ' Reason: %s' % (err))
        except socket.error, err:
            raise Error('Unable to reach the specified server.'
                ' Reason: %s' % (err))

        if SSL_END_MARKER not in cert:
            raise Error('No certificate found')
        
        cert = cert.replace(SSL_END_MARKER, '\n' + SSL_END_MARKER)

        fp = open(http_req.CUSTOM_CA_FILE, 'a')
        fp.write(cert)
        fp.close()

        http_req.compile_certs()

        return True
