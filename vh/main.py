from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder

from api import VHManager, Website



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

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        self.binder.reset().autodiscover().populate()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.manager.save()
        self.manager.update_configuration()
        self.context.notify('info', _('Saved'))