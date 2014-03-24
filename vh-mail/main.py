import os
import subprocess

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import str_fsize

from ajenti.plugins.vh.api import VHManager

from api import MailManager, ForwardingMailbox, ForwardingTarget, Mailbox


@plugin
class MailPlugin (SectionPlugin):
    def init(self):
        self.title = _('Mail')
        self.icon = 'envelope'
        self.category = 'Web'

        self.manager = MailManager.get()

        if not self.manager.is_configured:
            self.append(self.ui.inflate('vh-mail:not-configured'))
        else:
            self.post_init()

    @on('initial-enable', 'click')
    def on_initial_enable(self):
        self.post_init()
        self.manager.save()
        self.refresh()

    def post_init(self):
        self.empty()
        self.append(self.ui.inflate('vh-mail:main'))

        self.binder = Binder(None, self)

        def post_mb_bind(object, collection, item, ui):
            ui.find('size').text = str_fsize(self.manager.get_usage(item))

        def post_mb_update(object, collection, item, ui):
            if ui.find('password').value:
                item.password = ui.find('password').value

        self.find('mailboxes').post_item_bind = post_mb_bind
        self.find('mailboxes').post_item_update = post_mb_update
        self.find('mailboxes').filter = \
            lambda mb: self.context.session.identity in ['root', mb.owner]
        self.find('targets').new_item = lambda c: ForwardingTarget.create()

        self.binder.setup(self.manager.config)

    def _fetch_new_mailbox_name(self, cls):
        mb = cls.create()
        mb.local = self.find('new-mailbox-local').value
        mb.domain = self.find('new-mailbox-domain').value or \
            self.find('new-mailbox-domain-custom').value

        if not mb.local:
            self.context.notify('error', _('Invalid mailbox name'))
            return

        if not mb.domain:
            self.context.notify('error', _('Invalid mailbox domain'))
            return

        for existing in self.manager.config.mailboxes:
            if existing.name == mb.name:
                self.context.notify(
                    'error',
                    _('This address is already taken')
                )
                return

        self.find('new-mailbox-local').value = ''
        return mb

    @on('new-mailbox', 'click')
    def on_new_mailbox(self):
        self.binder.update()
        mb = self._fetch_new_mailbox_name(Mailbox)
        if not mb:
            return
        mb.owner = self.context.session.identity
        mb.password = ''
        self.manager.config.mailboxes.append(mb)
        self.manager.save()
        self.binder.populate()

    @on('new-forwarding-mailbox', 'click')
    def on_new_forwarding_mailbox(self):
        self.binder.update()
        mb = self._fetch_new_mailbox_name(ForwardingMailbox)
        if not mb:
            return
        mb.owner = self.context.session.identity
        self.manager.config.forwarding_mailboxes.append(mb)
        self.manager.save()
        self.binder.populate()

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        if not self.manager.is_configured:
            return

        domains = []
        for ws in VHManager.get().config.websites:
            if self.context.session.identity in ['root', ws.owner]:
                domains += [d.domain for d in ws.domains]
        domains = sorted(list(set(domains)))

        if self.find('new-mailbox-domain'):
            self.find('new-mailbox-domain').labels = \
                domains + [_('Custom domain')]
            self.find('new-mailbox-domain').values = domains + [None]

            if self.manager.is_configured:
                self.binder.unpopulate().populate()

        if os.path.exists(self.manager.config.dkim_private_key):
            pubkey = subprocess.check_output([
                'openssl', 'rsa', '-in', self.manager.config.dkim_private_key,
                '-pubout'
            ])
            pubkey = filter(None, pubkey.split('-'))[1].replace('\n', '')
            dns = '@\t\t\t\t10800 IN TXT "v=spf1 a -all"\n'
            dns += '_domainkey\t\t10800 IN TXT "o=~; r=postmaster@<domain>"\n'
            dns += '%s._domainkey\t10800 IN TXT "v=DKIM1; k=rsa; p="%s"\n' % (
                self.manager.config.dkim_selector,
                pubkey
            )
            dns += '_dmarc\t\t\t10800 IN TXT "v=DMARC1; p=quarantine; sp=r"\n'

            self.find('dkim-domain-entry').value = dns
        else:
            self.find('dkim-domain-entry').value = _('No valid key exists')

    @on('generate-dkim-key', 'click')
    def on_generate_dkim_key(self):
        self.binder.update()
        self.manager.generate_dkim_key()
        self.binder.populate()
        self.save()

    @on('generate-tls-cert', 'click')
    def on_generate_tls_cert(self):
        self.binder.update()
        self.manager.generate_tls_cert()
        self.binder.populate()
        self.save()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.manager.save()
        self.refresh()
        self.context.notify('info', _('Saved'))
