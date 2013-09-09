from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from api import VHManager, Website, WebsiteDomain, WebsitePort, WebsiteLocation, Backend



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
        
        def post_ws_bind(object, collection, item, ui):
            def create_location():
                t = ui.find('create-location-type').value
                l = WebsiteLocation.create(template=t)
                l.backend.type = t
                item.locations.append(l)
                self.refresh()
            ui.find('create-location').on('click', create_location)

        self.find('websites').post_item_bind = post_ws_bind

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