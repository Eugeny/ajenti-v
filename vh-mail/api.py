import grp
import json
import os
import pwd
import shutil
import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor

import templates


class Config (object):
    def __init__(self, j):
        self.mailboxes = [Mailbox(_) for _ in j.get('mailboxes', [])]
        self.mailroot = j.get('mailroot', '/var/vmail')
        self.custom_mta_config = j.get('custom_mta_config', '')
        self.custom_mta_acl = j.get('custom_mta_acl', '')
        self.custom_mta_routers = j.get('custom_mta_routers', '')
        self.custom_mta_transports = j.get('custom_mta_transports', '')

    @staticmethod
    def create():
        return Config({})

    def save(self):
        return {
            'mailboxes': [_.save() for _ in self.mailboxes],
            'custom_mta_acl': self.custom_mta_acl,
            'custom_mta_routers': self.custom_mta_routers,
            'custom_mta_config': self.custom_mta_config,
            'custom_mta_transports': self.custom_mta_transports,
        }


class Mailbox (object):
    def __init__(self, j):
        self.local = j.get('local', 'someone')
        self.domain = j.get('domain', 'example.com')
        self.password = j.get('password', 'example.com')
        self.owner = j.get('owner', 'root')

    @property
    def name(self):
        return '%s@%s' % (self.local, self.domain)

    @staticmethod
    def create():
        return Mailbox({})

    def save(self):
        return {
            'local': self.local,
            'domain': self.domain,
            'password': self.password,
            'owner': self.owner,
        }


@interface
class MailBackend (object):
    pass


@plugin
class MailEximCourierBackend (MailBackend):
    def init(self):
        self.exim_cfg_path = '/etc/exim4/exim4.conf'
        self.courier_authdaemonrc = '/etc/courier/authdaemonrc'
        self.courier_imaprc = '/etc/courier/imapd'
        self.courier_userdb = '/etc/courier/userdb'
        self.maildomains = '/etc/maildomains'
        self.mailuid = pwd.getpwnam('mail').pw_uid
        self.mailgid = grp.getgrnam('mail').gr_gid

    def configure(self, config):
        open(self.exim_cfg_path, 'w').write(templates.EXIM_CONFIG % {
            'mailname': open('/etc/mailname').read().strip(),
            'maildomains': self.maildomains,
            'mailroot': config.mailroot,
            'custom_mta_acl': config.custom_mta_acl,
            'custom_mta_routers': config.custom_mta_routers,
            'custom_mta_config': config.custom_mta_config,
            'custom_mta_transports': config.custom_mta_transports,
        })
        open(self.courier_authdaemonrc, 'w').write(templates.COURIER_AUTHRC)
        open(self.courier_imaprc, 'w').write(templates.COURIER_IMAP)

        os.chmod('/var/run/courier/authdaemon', 0755)

        if os.path.exists(self.courier_userdb):
            os.unlink(self.courier_userdb)

        if os.path.exists(self.maildomains):
            shutil.rmtree(self.maildomains)

        os.makedirs(self.maildomains)

        for mb in config.mailboxes:
            root = os.path.join(config.mailroot, mb.name)
            if not os.path.exists(root):
                os.makedirs(root)
                os.chown(root, self.mailuid, self.mailgid)


            with open(os.path.join(self.maildomains, mb.domain), 'a+') as f:
                f.write(mb.local + '\n')

            subprocess.call([
                'userdb', 
                mb.name, 
                'set', 
                'uid=mail',
                'gid=mail',
                'home=%s' % root,
                'mail=%s' % root,
            ])

            udbpw = subprocess.Popen(['userdbpw', '-md5'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            o, e = udbpw.communicate('%s\n%s\n' % (mb.password, mb.password))
            md5pw = o

            udb = subprocess.Popen(['userdb', mb.name, 'set', 'systempw'], stdin=subprocess.PIPE)
            udb.communicate(md5pw)

        subprocess.call(['makeuserdb'])

        ServiceMultiplexor.get().get_one('courier-authdaemon').restart()
        ServiceMultiplexor.get().get_one('courier-imap').restart()
        ServiceMultiplexor.get().get_one('exim4').command('reload')


@plugin
class MailManager (object):
    config_path = '/etc/ajenti/mail.json'

    def init(self):
        self.backend = MailBackend.get()

        if os.path.exists(self.config_path):
            self.is_configured = True
            self.config = Config(json.load(open(self.config_path)))
        else:
            self.is_configured = False
            self.config = Config.create()

    def get_usage(self, mb):
        return int(subprocess.check_output(
            ['du', '-sb', os.path.join(self.config.mailroot, mb.name)]
        ).split()[0])

    def save(self):
        j = json.dumps(self.config.save(), indent=4)
        with open(self.config_path, 'w') as f:
            f.write(j)
        os.chmod(self.config_path, 0600)
        self.is_configured = True

        self.backend.configure(self.config)
