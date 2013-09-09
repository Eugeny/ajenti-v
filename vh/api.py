import os
import json
from slugify import slugify

from ajenti.api import *

from webservers.nginx import NginxWebserver
from fcgi.phpfpm import PHPFPM


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


class WebsiteLocation (object):
    def __init__(self, j):
        self.pattern = j['pattern']
        self.match = j['match']
        self.backend = Backend(j['backend'])

    @staticmethod
    def create(template=None):
        templates = {
            'static': {
                'pattern': '/',
                'root': '',
                'match': 'exact',
                'backend': Backend.create().save(),
            },
            'php-fcgi': {
                'pattern': r'[^/]\.php(/|$)',
                'match': 'regex',
                'backend': Backend.create().save(),
            },
        }
        return WebsiteLocation(templates[template])

    def save(self):
        return {
            'pattern': self.pattern,
            'match': self.match,
            'backend': self.backend.save(),
        }


class WebsitePort (object):
    def __init__(self, j):
        self.port = j['port']
        self.ssl = j['ssl']

    @staticmethod
    def create(port):
        return WebsitePort({
            'port': port,
            'ssl': False,
        })

    def save(self):
        return {
            'port': self.port,
            'ssl': self.ssl,
        }


class Backend (object):
    def __init__(self, j):
        self.type = j['type']
        self.params = j.get('params', {})

    @staticmethod
    def create():
        return Backend({
            'type': 'static',
            'params': {}
        })

    def save(self):
        return {
            'type': self.type,
            'params': self.params,
        }


class Website (object):
    def __init__(self, j):
        self.name = j['name']
        self.slug = j.get('slug', slugify(self.name))
        self.domains = [WebsiteDomain(_) for _ in j['domains']]
        self.ports = [WebsitePort(_) for _ in j.get('ports', [])]
        self.locations = [WebsiteLocation(_) for _ in j.get('locations', [])]
        self.enabled = j.get('enabled', True)
        self.maintenance_mode = j.get('maintenance_mode', True)
        self.root = j.get('root', '/')

    @staticmethod
    def create(name):
        return Website({
            'name': name,
            'domains': [],
            'ports': [WebsitePort.create(80).save()],
        })

    def save(self):
        if not self.slug:
            self.slug = slugify(self.name)
        return {
            'name': self.name,
            'slug': self.slug,
            'domains': [_.save() for _ in self.domains],
            'ports': [_.save() for _ in self.ports],
            'locations': [_.save() for _ in self.locations],
            'enabled': self.enabled,
            'maintenance_mode': self.maintenance_mode,
            'root': self.root,
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
        self.fcgi_php = PHPFPM.get()

    def update_configuration(self):
        self.fcgi_php.create_configuration(self.config)
        self.webserver.create_configuration(self.config)

        self.fcgi_php.apply_configuration()
        self.webserver.apply_configuration()

    def save(self):
        j = json.dumps(self.config.save(), indent=4)
        open(self.config_path, 'w').write(j)
