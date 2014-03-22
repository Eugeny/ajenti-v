import os
import json
from slugify import slugify

from ajenti.api import *


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
        self.custom_conf = j.get('custom_conf', '')
        self.custom_conf_override = j.get('custom_conf_override', False)
        self.path = j.get('path', '')

    @staticmethod
    def create(template=None):
        templates = {
            'php-fcgi': {
                'pattern': r'[^/]\.php(/|$)',
                'match': 'regex',
                'backend': Backend.create().save(),
            },
        }

        default_template = {
            'pattern': '/',
            'match': 'exact',
            'backend': Backend.create().save(),
        }

        return WebsiteLocation(templates[template] if template in templates else default_template)

    def save(self):
        return {
            'pattern': self.pattern,
            'match': self.match,
            'backend': self.backend.save(),
            'custom_conf': self.custom_conf,
            'custom_conf_override': self.custom_conf_override,
            'path': self.path,
        }


class WebsitePort (object):
    def __init__(self, j):
        self.host = j.get('host', '*')
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
            'host': self.host,
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

    @property
    def typename(self):
        for cls in ApplicationGatewayComponent.get_classes():
            if cls.id == self.type:
                return cls.title

    def save(self):
        return {
            'type': self.type,
            'params': self.params,
        }


class Website (object):
    def __init__(self, j):
        self.name = j['name']
        self.owner = j.get('owner', 'root')
        self.ssl_cert_path = j.get('ssl_cert_path', '')
        self.ssl_key_path = j.get('ssl_key_path', '')
        self.domains = [WebsiteDomain(_) for _ in j['domains']]
        self.ports = [WebsitePort(_) for _ in j.get('ports', [])]
        self.locations = [WebsiteLocation(_) for _ in j.get('locations', [])]
        self.enabled = j.get('enabled', True)
        self.maintenance_mode = j.get('maintenance_mode', True)
        self.root = j.get('root', '/srv/new-website')
        self.extension_configs = j.get('extensions', {})
        self.custom_conf = j.get('custom_conf', '')
        self.slug = j.get('slug', slugify(self.name))

    @staticmethod
    def create(name):
        return Website({
            'name': name,
            'domains': [],
            'ports': [WebsitePort.create(80).save()],
        })

    def save(self):
        return {
            'name': self.name,
            'owner': self.owner,
            'domains': [_.save() for _ in self.domains],
            'ports': [_.save() for _ in self.ports],
            'locations': [_.save() for _ in self.locations],
            'enabled': self.enabled,
            'maintenance_mode': self.maintenance_mode,
            'root': self.root,
            'extensions': self.extension_configs,
            'custom_conf': self.custom_conf,
            'ssl_cert_path': self.ssl_cert_path,
            'ssl_key_path': self.ssl_key_path,
        }


@interface
class Component (object):
    def create_configuration(self, config):
        pass

    def apply_configuration(self):
        pass


@interface
class WebserverComponent (Component):
    pass


@interface
class ApplicationGatewayComponent (Component):
    id = None
    title = None


@interface
class MiscComponent (Component):
    pass


@plugin
class VHManager (object):
    config_path = '/etc/ajenti/vh.json'

    def init(self):
        if os.path.exists(self.config_path):
            self.is_configured = True
            self.config = Config(json.load(open(self.config_path)))
        else:
            self.is_configured = False
            self.config = Config.create()

        self.components = ApplicationGatewayComponent.get_all()
        self.components += MiscComponent.get_all()
        self.webserver = WebserverComponent.get()

    def update_configuration(self):
        for c in self.components:
            c.create_configuration(self.config)
        self.webserver.create_configuration(self.config)

        for c in self.components:
            c.apply_configuration()
        self.webserver.apply_configuration()

    def save(self):
        j = json.dumps(self.config.save(), indent=4)
        open(self.config_path, 'w').write(j)
        self.is_configured = True
