import os
import subprocess
import shutil
import tempfile
import uuid

from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import MiscComponent
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class VSFTPDExtension (BaseExtension):
    default_config = {
        'created': False,
        'user': None,
        'password': None,
    }
    name = 'FTP'

    def init(self):
        self.append(self.ui.inflate('vh-vsftpd:ext'))
        self.binder = Binder(self, self)

        self.config['username'] = self.website.slug

        if not self.config['created']:
            self.config['password'] = str(uuid.uuid4())
            self.config['created'] = True

        self.refresh()

    def refresh(self):
        self.binder.setup().populate()

    def update(self):
        pass


TEMPLATE_CONFIG = """
listen=YES
anonymous_enable=NO
local_enable=YES
guest_enable=YES
guest_username=www-data
nopriv_user=www-data
anon_root=/
xferlog_enable=YES
virtual_use_local_privs=YES
pam_service_name=vsftpd_virtual
user_config_dir=%s
chroot_local_user=YES
hide_ids=YES

force_dot_files=YES
local_umask=002
chmod_enable=YES
file_open_mode=0755

seccomp_sandbox=NO

"""

TEMPLATE_PAM = """#%%PAM-1.0
auth    required        pam_userdb.so   db=/etc/vsftpd/users
account required        pam_userdb.so   db=/etc/vsftpd/users
session required        pam_loginuid.so
"""

TEMPLATE_USER = """
local_root=%(root)s
allow_writeable_chroot=YES
write_enable=YES
"""


@plugin
class VSFTPD (MiscComponent):
    config_root = '/etc/vsftpd'
    config_root_users = '/etc/vsftpd.users.d'
    config_file = platform_select(
        debian='/etc/vsftpd.conf',
        arch='/etc/vsftpd.conf',
        centos='/etc/vsftpd/vsftpd.conf',
    )
    userdb_path = '/etc/vsftpd/users.db'
    pam_path = '/etc/pam.d/vsftpd_virtual'

    def create_configuration(self, config):
        if not os.path.exists(self.config_root):
            os.mkdir(self.config_root)
        if os.path.exists(self.config_root_users):
            shutil.rmtree(self.config_root_users)
        os.mkdir(self.config_root_users)

        pwfile = tempfile.NamedTemporaryFile(delete=False)
        pwpath = pwfile.name
        for website in config.websites:
            subprocess.call(['chgrp', 'ftp', website.root])
            subprocess.call(['chmod', 'g+w', website.root])
            if website.enabled:
                cfg = website.extension_configs.get(VSFTPDExtension.classname)
                if cfg and cfg['created']:
                    pwfile.write('%s\n%s\n' % (cfg['username'], cfg['password']))
                    open(os.path.join(self.config_root_users, cfg['username']), 'w').write(
                        TEMPLATE_USER % {
                            'root': website.root,
                        }
                    )
        pwfile.close()

        subprocess.call(['db_load', '-T', '-t', 'hash', '-f', pwpath, self.userdb_path])
        os.unlink(pwpath)
        open(self.pam_path, 'w').write(TEMPLATE_PAM)
        open(self.config_file, 'w').write(TEMPLATE_CONFIG % self.config_root_users)

        if not os.path.exists('/var/www'):
            os.mkdir('/var/www')
        subprocess.call(['chown', 'www-data:', '/var/www'])

    def apply_configuration(self):
        ServiceMultiplexor.get().get_one('vsftpd').restart()
