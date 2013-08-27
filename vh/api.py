import os
import json
from slugify import slugify

from ajenti.api import *

from webservers.nginx import NginxWebserver


class Config (object):
    def __init__(self, j):
        self.websites = [Website(_) for _ in j['websites']]

    @staticmethod
    def create():
        return Config({
            'websites': []
        })

    def save(self):
        return {
            'websites': [_.save() for _ in self.websites],
        }


class WebsiteDomain (object):
    def __init__(self, j):
        self.domain = j['domain']

    @staticmethod
    def create(domain):
        return WebsiteDomain({
            'domain': domain,
        })

    def save(self):
        return {
            'domain': self.domain,
        }


class Website (object):
    def __init__(self, j):
        self.name = j['name']
        self.slug = j.get('slug', slugify(self.name))
        self.domains = [WebsiteDomain(_) for _ in j['domains']]
        self.enabled = j.get('enabled', False)
        self.maintenance_mode = j.get('maintenance_mode', False)

    @staticmethod
    def create(name):
        return Website({
            'name': name,
            'slug': None,
            'domains': [],
            'enabled': True,
            'maintenance_mode': True,
        })

    def save(self):
        if not self.slug:
            self.slug = slugify(self.name)
        return {
            'name': self.name,
            'slug': self.slug,
            'domains': [_.save() for _ in self.domains],
            'enabled': self.enabled,
            'maintenance_mode': self.maintenance_mode,
        }


@plugin
class VHManager (object):
    config_path = '/etc/ajenti/vh.json'

    def init(self):
        if os.path.exists(self.config_path):
            self.config = Config(json.load(open(self.config_path)))
        else:
            self.config = Config.create()
        self.webserver = NginxWebserver.get()

    def update_configuration(self):
        self.webserver.create_configuration(self.config)
        self.webserver.apply_configuration()

    def save(self):
        j = json.dumps(self.config.save(), indent=4)
        open(self.config_path, 'w').write(j)
