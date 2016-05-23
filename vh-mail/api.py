import grp
import json
import os
import pwd
import shutil
import subprocess

import ajenti
from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import Restartable
from ajenti.plugins.vh.processes import SupervisorRestartable
from ajenti.util import platform_select

import templates


class Config (object):
    def __init__(self, j):
        self.mailboxes = [Mailbox(_) for _ in j.get('mailboxes', [])]
        self.forwarding_mailboxes = [
            ForwardingMailbox(_)
            for _ in j.get('forwarding_mailboxes', [])
        ]
        self.mailroot = j.get('mailroot', '/var/vmail')
        self.custom_mta_config = j.get('custom_mta_config', '')
        self.custom_mta_acl = j.get('custom_mta_acl', '')
        self.custom_mta_routers = j.get('custom_mta_routers', '')
        self.custom_mta_local_router = j.get('custom_mta_local_router', '')
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
            'forwarding_mailboxes': [
                _.save()
                for _ in self.forwarding_mailboxes
            ],
            'custom_mta_acl': self.custom_mta_acl,
            'custom_mta_routers': self.custom_mta_routers,
            'custom_mta_local_router': self.custom_mta_local_router,
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


class ForwardingMailbox (object):
    def __init__(self, j):
        self.targets = [ForwardingTarget(_) for _ in j.get('targets', [])]
        self.local = j.get('local', 'someone')
        self.domain = j.get('domain', 'example.com')
        self.owner = j.get('owner', 'root')

    @property
    def name(self):
        return '%s@%s' % (self.local, self.domain)

    @staticmethod
    def create():
        return ForwardingMailbox({})

    def save(self):
        return {
            'targets': [_.save() for _ in self.targets],
            'local': self.local,
            'domain': self.domain,
            'owner': self.owner,
        }


class ForwardingTarget (object):
    def __init__(self, j):
        self.email = j.get('email', 'someone@example.com')

    @staticmethod
    def create():
        return ForwardingTarget({})

    def save(self):
        return {
            'email': self.email,
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
            arch='/etc/mail/exim.conf',
        )

        for d in ['/etc/courier', '/var/run/courier']:
            if not os.path.exists(d):
                os.makedirs(d)

        self.courier_authdaemonrc = platform_select(
            debian='/etc/courier/authdaemonrc',
            centos='/etc/authlib/authdaemonrc',
            arch='/etc/authlib/authdaemonrc',
        )
        self.courier_imaprc = platform_select(
            debian='/etc/courier/imapd',
            centos='/usr/lib/courier-imap/etc/imapd',
            arch='/etc/courier-imap/imapd',
        )
        self.courier_imapsrc = platform_select(
            debian='/etc/courier/imapd-ssl',
            centos='/usr/lib/courier-imap/etc/imapd-ssl',
            arch='/etc/courier-imap/imapd-ssl',
        )
        self.courier_userdb = platform_select(
            debian='/etc/courier/userdb',
            centos='/etc/authlib/userdb',
            arch='/etc/authlib/userdb',
        )
        self.courier_authsocket = platform_select(
            debian='/var/run/courier/authdaemon/socket',
            centos='/var/spool/authdaemon/socket',
            arch='/var/run/authdaemon/socket',
        )

        self.maildomains = '/etc/exim.domains'
        self.mailforward = '/etc/exim.forward'
        self.mailuid = pwd.getpwnam('mail').pw_uid
        self.mailgid = grp.getgrnam('mail').gr_gid

    def configure(self, config):
        try:
            mailname = open('/etc/mailname').read().strip()
        except:
            mailname = 'localhost'

        domains = [x.domain for x in config.mailboxes]
        domains += [x.domain for x in config.forwarding_mailboxes]
        domains = list(set(domains))
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
            'mailforward': self.mailforward,
            'mailroot': config.mailroot,
            'custom_mta_acl': config.custom_mta_acl,
            'custom_mta_routers': config.custom_mta_routers,
            'custom_mta_local_router': config.custom_mta_local_router,
            'custom_mta_config': config.custom_mta_config,
            'custom_mta_transports': config.custom_mta_transports,
            'dkim_enable': 'DKIM_ENABLE=1' if config.dkim_enable else '',
            'dkim_selector': config.dkim_selector,
            'dkim_private_key': config.dkim_private_key,
            'tls_enable': 'TLS_ENABLE=1' if config.tls_enable else '',
            'tls_certificate': config.tls_certificate,
            'tls_privatekey': config.tls_privatekey,
            'courier_authsocket': self.courier_authsocket,
        })
        os.chmod(self.exim_cfg_path, 0644)
        open(self.courier_authdaemonrc, 'w').write(templates.COURIER_AUTHRC % {
            'courier_authsocket': self.courier_authsocket,
        })
        open(self.courier_imaprc, 'w').write(templates.COURIER_IMAP % {
        })
        open(self.courier_imapsrc, 'w').write(templates.COURIER_IMAPS % {
            'tls_pem': pem_path,
        })

        if os.path.exists(self.courier_authsocket):
            os.chmod(self.courier_authsocket, 0755)
        
        socketdir = os.path.split(self.courier_authsocket)[0]
        if os.path.exists(socketdir):
            os.chmod(socketdir, 0755)

        # Domain entries ----------------------------

        if os.path.exists(self.maildomains):
            shutil.rmtree(self.maildomains)
        os.makedirs(self.maildomains)
        os.chmod(self.maildomains, 0755)

        for mb in config.mailboxes:
            root = os.path.join(config.mailroot, mb.name)
            newroot = os.path.join(config.mailroot, mb.domain, mb.local)
            
            if not os.path.exists(newroot):                
                if os.path.exists(root):
                    os.renames(root, newroot)
                else:
                    for d in ['new', 'cur', 'tmp']:
                        os.makedirs(os.path.join(newroot, d))
                #os.chown(newroot, self.mailuid, self.mailgid)
                subprocess.call(['chown', '-R', 'mail:mail', newroot])

            with open(os.path.join(self.maildomains, mb.domain), 'a+') as f:
                f.write(mb.local + '\n')
            os.chmod(os.path.join(self.maildomains, mb.domain), 0755)

        # Forwarding entries ----------------------------

        if os.path.exists(self.mailforward):
            shutil.rmtree(self.mailforward)
        os.makedirs(self.mailforward)
        os.chmod(self.mailforward, 0755)

        for mb in config.forwarding_mailboxes:
            fpath = os.path.join(
                self.mailforward,
                '%s@%s' % (mb.local, mb.domain)
            )
            with open(fpath, 'a+') as f:
                for target in mb.targets:
                    f.write(target.email + ',')
                if any(x.local == mb.local and x.domain == mb.domain for x in config.mailboxes):
                    f.write(mb.local + '@' + mb.domain)
            os.chmod(fpath, 0755)

        # UserDB ------------------------------------

        if os.path.exists(self.courier_userdb):
            os.unlink(self.courier_userdb)

        for mb in config.mailboxes:
            root = os.path.join(config.mailroot, mb.domain, mb.local)
            subprocess.call([
                'userdb',
                mb.name,
                'set',
                'uid=%s' % self.mailuid,
                'gid=%s' % self.mailgid,
                'home=%s' % root,
                'mail=%s' % root,
            ])
            
            if mb.password[:len("md5|")]=="md5|":    #Check if the stored password is encrypted with md5 algorithm already
                md5pw=mb.password[len("md5|"):]
                
            else:                                    #If stored password is not encrypted (i.e. plaintext), then encrypty it with md5
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

        if os.path.exists(self.courier_userdb):
            os.chmod(self.courier_userdb, 0600)

        subprocess.call(['makeuserdb'])

        EximRestartable.get().restart()
        CourierIMAPRestartable.get().restart()
        CourierAuthRestartable.get().restart()


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
        try:
            return int(subprocess.check_output(
                ['du', '-sb', os.path.join(self.config.mailroot, mb.domain, mb.local)]
            ).split()[0])
        except:
            return 0

    def save(self):
        j = json.dumps(self.config.save(), indent=4)
        with open(self.config_path, 'w') as f:
            f.write(j)
        os.chmod(self.config_path, 0600)
        self.is_configured = True

        self.backend.configure(self.config)

    def generate_tls_cert(self):
        if not os.path.exists(self.tls_path):
            os.makedirs(self.tls_path)
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
            os.makedirs(self.dkim_path)

        privkey_path = os.path.join(self.dkim_path, 'private.key')

        subprocess.call([
            'openssl', 'genrsa', '-out', privkey_path, '2048'
        ])

        self.config.dkim_enable = True
        self.config.dkim_private_key = privkey_path


@plugin
class EximRestartable (Restartable):
    paniclog = platform_select(
        debian='/var/log/exim4/paniclog',
        default='/var/log/exim/paniclog',
    )

    def restart(self):
        open(self.paniclog, 'w').close()

        ServiceMultiplexor.get().get_one(platform_select(
            debian='exim4',
            default='exim',
        )).command('restart')


@plugin
class CourierIMAPRestartable (Restartable):
    def restart(self):
        ServiceMultiplexor.get().get_one(platform_select(
            debian='courier-imap',
            centos='courier-imap',
            default='courier-imapd',
        )).restart()
        if ajenti.platform != 'centos':  # centos runs both
            ServiceMultiplexor.get().get_one(platform_select(
                debian='courier-imap-ssl',
                default='courier-imapd-ssl',
            )).restart()


@plugin
class CourierAuthRestartable (Restartable):
    def restart(self):
        ServiceMultiplexor.get().get_one(platform_select(
            debian='courier-authdaemon',
            centos='courier-authlib',
        )).restart()