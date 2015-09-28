import gevent
import logging
import os
import subprocess
from slugify import slugify

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.users import UserManager

from api import VHManager, Website, WebsiteDomain, WebsitePort, WebsiteLocation, ApplicationGatewayComponent
from extensions import BaseExtension


@plugin
class WebsitesPlugin (SectionPlugin):
    def init(self):
        self.title = _('Websites')
        self.icon = 'globe'
        self.category = 'Web'
        self.order = 1

        self.manager = VHManager.get()

        if not self.manager.is_configured:
            from ajenti.plugins.vh import destroyed_configs
            self.append(self.ui.inflate('vh:not-configured'))
            self.find('destroyed-configs').text = ', '.join(destroyed_configs)
        else:
            self.post_init()

    @on('initial-enable', 'click')
    def on_initial_enable(self):
        self.post_init()
        self.manager.save()
        self.refresh()

    def post_init(self):
        self.empty()
        self.append(self.ui.inflate('vh:main'))

        self.binder = Binder(None, self)

        def post_ws_bind(object, collection, item, ui):
            def manage():
                self.context.launch('v:manage-website', website=item)
            ui.find('manage').on('click', manage)

        self.find('websites').post_item_bind = post_ws_bind
        self.find('websites').filter = lambda ws: self.context.session.identity in ['root', ws.owner]

        self.binder.setup(self.manager)

    @on('new-website', 'click')
    def on_new_website(self):
        self.binder.update()
        name = self.find('new-website-name').value
        self.find('new-website-name').value = ''
        if not name:
            name = '_'

        slug = slugify(name)
        slugs = [x.slug for x in self.manager.config.websites]
        while slug in slugs:
            slug += '_'

        w = Website.create(name)
        w.slug = slug
        w.owner = self.context.session.identity
        self.manager.config.websites.append(w)
        self.manager.save()
        self.binder.populate()

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        if self.manager.is_configured:
            self.manager.config.websites = sorted(self.manager.config.websites, key=lambda x: x.name)
            self.binder.setup().populate()

    @on('recheck', 'click')
    def on_recheck(self):
        self.binder.update()
        self.context.endpoint.send_progress(_('Testing configuration'))
        try:
            self.manager.run_checks()
        finally:
            self.context.endpoint.send_progress(None)
            self.refresh()

    @on('save', 'click')
    def save(self):
        self.context.endpoint.send_progress(_('Saving changes'))
        self.binder.update()
        self.manager.save()
        self.context.endpoint.send_progress(_('Applying changes'))
        self.manager.update_configuration()
        self.context.endpoint.send_progress(_('Restarting web services'))
        self.manager.restart_services()
        gevent.spawn(self.on_recheck)
        self.refresh()
        self.context.notify('info', _('Saved'))


@plugin
class WebsitesWebsiteEditorPlugin (SectionPlugin):
    uses_access_permission_of = WebsitesPlugin

    def init(self):
        self.title = 'Website editor'
        self.icon = 'globe'
        self.category = 'Web'
        self.order = 2
        self.hidden = True

        self.manager = VHManager.get()
        self.binder = Binder(None, self)

        self.append(self.ui.inflate('vh:main-website'))
        self.find('domains').new_item = lambda c: WebsiteDomain.create('example.com')
        self.find('ports').new_item = lambda c: WebsitePort.create(80)

        def post_location_bind(object, collection, item, ui):
            ui.find('backend-params').empty()
            ui.find('backend-params').append(self.ui.inflate('vh:main-backend-params-%s' % item.backend.type))
            item.backend.__binder = Binder(item.backend, ui.find('backend-params'))
            item.backend.__binder.populate()

        def post_location_update(object, collection, item, ui):
            item.backend.__binder.update()

        self.find('locations').post_item_bind = post_location_bind
        self.find('locations').post_item_update = post_location_update

        self.find('create-location-type').labels = []
        self.find('create-location-type').values = []
        for g in sorted(ApplicationGatewayComponent.get_classes(), key=lambda x: x.title):
            self.find('create-location-type').labels.append(g.title)
            self.find('create-location-type').values.append(g.id)

    @intent('v:manage-website')
    def on_launch(self, website=None):
        self.activate()
        self.website = website
        self.binder.setup(self.website)
        self.binder.populate()

        for ext in BaseExtension.get_classes():
            ext.selftest()

        extensions = BaseExtension.get_classes()

        def create_location():
            self.binder.update()
            t = self.find('create-location-type').value
            l = WebsiteLocation.create(self.website, template=t)
            l.backend.type = t
            self.website.locations.append(l)
            self.refresh()
        self.find('create-location').on('click', create_location)

        # Extensions
        for tab in list(self.find('tabs').children):
            if hasattr(tab, '-is-extension'):
                tab.delete()

        self.website.extensions = []
        for ext in extensions:
            ext = ext.new(self.ui, self.website, config=self.website.extension_configs.get(ext.classname, None))
            ext.editor_ui = self
            ext._ui_container = self.ui.create('tab', children=[ext], title=ext.name)
            setattr(ext._ui_container, '-is-extension', True)
            self.website.extensions.append(ext)
            self.find('tabs').append(ext._ui_container)

        # Root creator
        self.find('root-not-created').visible = not os.path.exists(self.website.root)

        def create_root():
            self.binder.update()
            if not os.path.exists(self.website.root):
                os.makedirs(self.website.root)
            subprocess.call(['chown', '-R', 'www-data:', self.website.root])
            self.save()

        self.find('create-root-directory').on('click', create_root)
        self.find('fix-root-permissions').on('click', create_root)
        self.find('set-path').on('click', self.save)

        # Downloader

        def download():
            url = self.find('download-url').value
            self.save()
            tmppath = '/tmp/ajenti-v-download'
            script = 'wget "%s" -O "%s" ' % (url, tmppath)
            if url.lower().endswith(('tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2')):
                script += '&& tar xf "%s" -C "%s"' % (tmppath, self.website.root)
            elif url.lower().endswith('.rar'):
                script += '&& unrar x "%s" "%s"' % (tmppath, self.website.root)
            elif url.lower().endswith('.zip'):
                script += '&& unzip "%s" -d "%s"' % (tmppath, self.website.root)

            script += ' && chown www-data: -R "%s"' % self.website.root
            script += ' && find "%s" -type d -exec chmod 775 {} ";"' % self.website.root
            script += ' && find "%s" -type f -exec chmod 644 {} ";"' % self.website.root

            def callback():
                self.save()
                self.activate()
                if os.path.exists(tmppath):
                    os.unlink(tmppath)
                self.context.notify('info', _('Download complete'))

            self.context.launch('terminal', command=script, callback=callback)

        self.find('download').on('click', download)

    @on('go-back', 'click')
    def on_go_back(self):
        WebsitesPlugin.get().activate()

    @on('destroy', 'click')
    def on_destroy(self):
        for ext in self.website.extensions:
            try:
                ext.on_destroy()
            except Exception, e:
                logging.error(str(e))
        self.manager.config.websites.remove(self.website)
        self.save()
        self.on_go_back()

    def refresh(self):
        self.binder.unpopulate().populate()

    def run_checks(self):
        self.context.endpoint.send_progress(_('Testing configuration'))
        try:
            self.manager.run_checks()
        finally:
            self.context.endpoint.send_progress(None)
            self.refresh()

    def save_data(self):
        self.binder.update()
        for ext in self.website.extensions:
            ext.update()
            self.website.extension_configs[ext.classname] = ext.config
        self.manager.save()

    @on('save', 'click')
    def save(self):
        self.save_data()
        self.context.endpoint.send_progress(_('Applying changes'))
        self.manager.update_configuration()
        self.context.endpoint.send_progress(_('Restarting web services'))
        self.manager.restart_services()
        gevent.spawn(self.run_checks)
        self.refresh()
        self.context.notify('info', _('Saved'))
