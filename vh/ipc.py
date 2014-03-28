import json
import os

from ajenti.api import *
from ajenti.ipc import IPCHandler
from ajenti.plugins import manager

from api import VHManager


@plugin
class VIPC (IPCHandler):
    def init(self):
        self.manager = VHManager.get()

    def get_name(self):
        return 'v'

    def handle(self, args):
        command = args[0]
        if command in ['import', 'export']:
            config = json.load(open(self.manager.config_path))

            if command == 'export':
                if len(args) == 1:
                    raise Exception('Usage: v export <website name>')
                matching = [
                    x for x in config['websites']
                    if x['name'] == args[1]
                ]
                if len(matching) == 0:
                    raise Exception('Website not found')
                return json.dumps(matching[0], indent=4)

            if command == 'import':
                if len(args) == 1:
                    raise Exception('Usage: v import <website config file>')
                path = args[1]
                if not os.path.exists(path):
                    raise Exception('Config does not exist')
                website_config = json.load(open(path))
                websites = [
                    x for x in config['websites']
                    if x['name'] != website_config['name']
                ]
                websites.append(website_config)
                config['websites'] = websites
                with open(self.manager.config_path, 'w') as f:
                    json.dump(config, f)
                self.manager.reload()
                return 'OK'

        if command == 'apply':
            self.manager.update_configuration()
            return 'OK'
