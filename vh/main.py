from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from api import VHManager, Website, WebsiteDomain, WebsitePort, WebsiteLocation
from extensions.base import BaseExtension


@plugin
class WebsitesPlugin (SectionPlugin):
    def init(self):
        self.title = _('Websites')
        self.icon = 'globe'
        self.category = 'Web'

        self.append(self.ui.inflate('vh:main'))

        self.manager = VHManager.get()
        self.binder = Binder(self.manager.config, self)
        self.find('websites').new_item = lambda c: Website.create('New Website')
        self.find('domains').new_item = lambda c: WebsiteDomain.create('example.com')
        self.find('ports').new_item = lambda c: WebsitePort.create(80)
        
        extensions = BaseExtension.get_classes()

        def post_ws_bind(object, collection, item, ui):
            def create_location():
                t = ui.find('create-location-type').value
                l = WebsiteLocation.create(template=t)
                l.backend.type = t
                item.locations.append(l)
                self.binder.update()
                self.refresh()
            ui.find('create-location').on('click', create_location)

            if hasattr(item, 'extensions'):
                for ext in item.extensions:
                    ext._ui_container.delete()

            item.extensions = []
            for ext in extensions:
                ext = ext.new(self.ui, item, config=item.extension_configs.get(ext.classname, None))
                ext._ui_container = self.ui.create('tab', children=[ext], title=ext.name)
                item.extensions.append(ext)
                ui.find('tabs').append(ext._ui_container)

        def post_ws_update(object, collection, item, ui):
            for ext in item.extensions:
                item.extension_configs[ext.classname] = ext.config

        self.find('websites').post_item_bind = post_ws_bind
        self.find('websites').post_item_update = post_ws_update

        self.binder.autodiscover()

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.binder.reset().populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.manager.save()
        self.manager.update_configuration()
        self.refresh()
        self.context.notify('info', _('Saved'))