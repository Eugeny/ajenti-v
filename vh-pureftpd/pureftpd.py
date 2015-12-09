import os
import subprocess
import uuid

import ajenti
from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import MiscComponent
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class PureFTPDExtension (BaseExtension):
    default_config = {
        'created': False,
        'password': None,
    }
    name = 'FTP'

    def init(self):
        self.append(self.ui.inflate('vh-pureftpd:ext'))
        self.binder = Binder(self, self)

        if not 'username' in self.config:
            self.config['username'] = self.website.slug

        if not self.config['created']:
            self.config['password'] = str(uuid.uuid4())
            self.config['path'] = self.website.root
            self.config['created'] = True

        self.refresh()

    def refresh(self):
        self.binder.setup().populate()

    def update(self):
        self.binder.update()



CENTOS_CONFIG = """
ChrootEveryone              yes
BrokenClientsCompatibility  no
MaxClientsNumber            50
Daemonize                   yes
MaxClientsPerIP             8
VerboseLog                  no
DisplayDotFiles             yes
AnonymousOnly               no
NoAnonymous                 yes
SyslogFacility              ftp
DontResolve                 yes
MaxIdleTime                 15
PureDB                      /etc/pure-ftpd/pureftpd.pdb
PAMAuthentication             yes
LimitRecursion              10000 8
Umask                       133:022
MinUID                      1
UseFtpUsers                 no
AllowUserFXP                yes
ProhibitDotFilesWrite       no
ProhibitDotFilesRead        no
AutoRename                  no
AltLog                      clf:/var/log/pureftpd.log
TLS                         1
"""


@plugin
class PureFTPD (MiscComponent):
    userdb_path = '/etc/pure-ftpd/pureftpd.passwd'
    config_path = platform_select(
        centos='/etc/pure-ftpd/pure-ftpd.conf',
        arch='/etc/pure-ftpd.conf',
    )

    def create_configuration(self, config):
        open(self.userdb_path, 'w').close()
        for website in config.websites:
            if website.enabled:
                cfg = website.extension_configs.get(PureFTPDExtension.classname)
                if cfg and cfg['created']:
                    p = subprocess.Popen(
                        [
                            'pure-pw', 'useradd', cfg['username'], '-u', 'www-data',
                            '-d', cfg['path'] or website.root,
                        ],
                        stdin=subprocess.PIPE
                    )
                    p.communicate('%s\n%s\n' % (cfg['password'], cfg['password']))

        subprocess.call(['pure-pw', 'mkdb'])

        if ajenti.platform == 'debian':
            open('/etc/pure-ftpd/conf/MinUID', 'w').write('1')
            authfile = '/etc/pure-ftpd/auth/00puredb'
            if not os.path.exists(authfile):
                os.symlink('/etc/pure-ftpd/conf/PureDB', authfile)
        if ajenti.platform in ['arch', 'centos']:
            open(self.config_path, 'w').write(CENTOS_CONFIG)

    def apply_configuration(self):
        ServiceMultiplexor.get().get_one('pure-ftpd').restart()
