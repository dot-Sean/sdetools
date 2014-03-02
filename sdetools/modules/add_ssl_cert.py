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
            default='')
        self.config.opts.add('port', "Port to connect to",
            default='443')
        self.config.opts.add('custom_cert', "Certificate to import",
            default='')

    def handle(self):
        if self.config['custom_cert'] == '' or not self.config['custom_cert']:
            # If no custom_cert specified, try fetching the cert from the server
            if self.config['server'] == '' or not self.config['server']:
                raise UsageError('No server specified')
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
        else:
            if SSL_END_MARKER in self.config['custom_cert']:
                # Use input, if it is a certificate
                cert = self.config['custom_cert']
            else:
                # Try opening the specified certificate
                try:
                    cert = open(self.config['custom_cert'],'r').read()
                except IOError, err:
                    raise Error('Unable to open file. Reason: %s' % (err))

        if SSL_END_MARKER not in cert:
            raise Error('No certificate found')

        fp = open(http_req.CUSTOM_CA_FILE, 'a')
        fp.write(cert)
        fp.close()

        http_req.compile_certs()

        return True
