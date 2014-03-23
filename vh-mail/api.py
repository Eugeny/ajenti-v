import grp
import json
import os
import pwd
import shutil
import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.util import platform_select

import templates


class Config (object):
    def __init__(self, j):
        self.mailboxes = [Mailbox(_) for _ in j.get('mailboxes', [])]
        self.mailroot = j.get('mailroot', '/var/vmail')
        self.custom_mta_config = j.get('custom_mta_config', '')
        self.custom_mta_acl = j.get('custom_mta_acl', '')
        self.custom_mta_routers = j.get('custom_mta_routers', '')
        self.custom_mta_transports = j.get('custom_mta_transports', '')
        self.dkim_enable = j.get('dkim_enable', False)
        self.dkim_selector = j.get('dkim_selector', 'x')
        self.dkim_private_key = j.get('dkim_private_key', '')
        self.tls_enable = j.get('tls_enable', False)
        self.tls_certificate = j.get('tls_certificate', '')
        self.tls_privatekey = j.get('tls_privatekey', '')

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
            'dkim_enable': self.dkim_enable,
            'dkim_selector': self.dkim_selector,
            'dkim_private_key': self.dkim_private_key,
            'tls_enable': self.tls_enable,
            'tls_certificate': self.tls_certificate,
            'tls_privatekey': self.tls_privatekey,
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
        self.exim_cfg_path = platform_select(
            debian='/etc/exim4/exim4.conf',
            centos='/etc/exim/exim.conf',
        )

        for d in ['/etc/courier', '/var/run/courier']:
            if not os.path.exists(d):
                os.mkdir(d)

        self.courier_authdaemonrc = platform_select(
            debian='/etc/courier/authdaemonrc',
            centos='/etc/authlib/authdaemonrc',
        )
        self.courier_imaprc = platform_select(
            debian='/etc/courier/imapd',
            centos='/usr/lib/courier-imap/etc/imapd',
        )
        self.courier_imapsrc = platform_select(
            debian='/etc/courier/imapd-ssl',
            centos='/usr/lib/courier-imap/etc/imapd-ssl',
        )
        self.courier_userdb = platform_select(
            debian='/etc/courier/userdb',
            centos='/etc/authlib/userdb',
        )

        self.maildomains = '/etc/maildomains'
        self.mailuid = pwd.getpwnam('mail').pw_uid
        self.mailgid = grp.getgrnam('mail').gr_gid

    def configure(self, config):
        try:
            mailname = open('/etc/mailname').read().strip()
        except:
            mailname = 'localhost'

        domains = list(set(x.domain for x in config.mailboxes))
        if not mailname in domains:
            domains.append(mailname)
        if not 'localhost' in domains:
            domains.append('localhost')

        pem_path = os.path.join('/etc/courier/mail.pem')
        pem = ''
        if os.path.exists(config.tls_certificate):
            pem += open(config.tls_certificate).read()
        if os.path.exists(config.tls_privatekey):
            pem += open(config.tls_privatekey).read()
        with open(pem_path, 'w') as f:
            f.write(pem)

        open(self.exim_cfg_path, 'w').write(templates.EXIM_CONFIG % {
            'local_domains': ' : '.join(domains),
            'mailname': mailname,
            'maildomains': self.maildomains,
            'mailroot': config.mailroot,
            'custom_mta_acl': config.custom_mta_acl,
            'custom_mta_routers': config.custom_mta_routers,
            'custom_mta_config': config.custom_mta_config,
            'custom_mta_transports': config.custom_mta_transports,
            'dkim_enable': 'DKIM_ENABLE=1' if config.dkim_enable else '',
            'dkim_selector': config.dkim_selector,
            'dkim_private_key': config.dkim_private_key,
            'tls_enable': 'TLS_ENABLE=1' if config.tls_enable else '',
            'tls_certificate': config.tls_certificate,
            'tls_privatekey': config.tls_privatekey,
        })
        open(self.courier_authdaemonrc, 'w').write(templates.COURIER_AUTHRC)
        open(self.courier_imaprc, 'w').write(templates.COURIER_IMAP % {
        })
        open(self.courier_imapsrc, 'w').write(templates.COURIER_IMAPS % {
            'tls_pem': pem_path,
        })

        if os.path.exists('/var/run/courier/authdaemon'):
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
                'uid=%s' % self.mailuid,
                'gid=%s' % self.mailgid,
                'home=%s' % root,
                'mail=%s' % root,
            ])

            udbpw = subprocess.Popen(
                ['userdbpw', '-md5'],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            o, e = udbpw.communicate(
                '%s\n%s\n' % (mb.password, mb.password)
            )
            md5pw = o

            udb = subprocess.Popen(
                ['userdb', mb.name, 'set', 'systempw'],
                stdin=subprocess.PIPE
            )
            udb.communicate(md5pw)

        subprocess.call(['makeuserdb'])

        ServiceMultiplexor.get().get_one(platform_select(
            debian='courier-authdaemon',
            centos='courier-authlib',
        )).restart()
        ServiceMultiplexor.get().get_one('courier-imap').restart()
        ServiceMultiplexor.get().get_one(platform_select(
            debian='courier-imap-ssl',
            centos='courier-imap',
        )).restart()
        ServiceMultiplexor.get().get_one(platform_select(
            debian='exim4',
            centos='exim',
        )).command('restart')


@plugin
class MailManager (BasePlugin):
    config_path = '/etc/ajenti/mail.json'
    dkim_path = platform_select(
        debian='/etc/exim4/dkim/',
        centos='/etc/exim/dkim/',
    )
    tls_path = platform_select(
        debian='/etc/exim4/tls/',
        centos='/etc/exim/tls/',
    )

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

    def generate_tls_cert(self):
        if not os.path.exists(self.tls_path):
            os.mkdir(self.tls_path)
        key_path = os.path.join(self.tls_path, 'mail.key')
        cert_path = os.path.join(self.tls_path, 'mail.crt')
        openssl = subprocess.Popen([
            'openssl', 'req', '-x509', '-newkey', 'rsa:1024',
            '-keyout', key_path, '-out', cert_path, '-days', '4096',
            '-nodes'
        ])
        openssl.communicate('\n\n\n\n\n\n\n\n\n\n\n\n')
        self.config.tls_enable = True
        self.config.tls_certificate = cert_path
        self.config.tls_privatekey = key_path

    def generate_dkim_key(self):
        if not os.path.exists(self.dkim_path):
            os.mkdir(self.dkim_path)

        privkey_path = os.path.join(self.dkim_path, 'private.key')

        subprocess.call([
            'openssl', 'genrsa', '-out', privkey_path, '2048'
        ])

        self.config.dkim_enable = True
        self.config.dkim_private_key = privkey_path
