import os
import shutil
import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import ApplicationGatewayComponent
from ajenti.util import platform_select

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData



@plugin
class Puma (ApplicationGatewayComponent):
    id = 'ruby-puma'
    title = 'Ruby Puma'

    def __generate_website(self, website):
        i = 0
        for location in website.locations:
            if location.backend.type == 'ruby-puma':
                i += 1
                location.backend.id = website.slug + '-ruby-puma-' + str(i)

    def create_configuration(self, config):
        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()
        for p in sup.tree.programs:
            if p.command.startswith('puma') or p.command.startswith('bundle exec puma'):
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                for location in website.locations:
                    if location.backend.type == 'ruby-puma':
                        self.__generate_website(website)
                        p = ProgramData()
                        p.name = location.backend.id
                        bundler = location.backend.params.get('bundler', True)
                        workers = location.backend.params.get('workers', 4)
                        environment = location.backend.params.get('environment', 4)
                        p.command = 'puma -e %s -t %i -b unix:///var/run/puma-%s.sock' % (
                            environment, workers, location.backend.id
                        )
                        if bundler:
                            p.command = 'bundle exec ' + p.command
                        p.environment = 'HOME="%s"' % website.root
                        p.directory = website.root
                        sup.tree.programs.append(p)

        sup.save()

    def apply_configuration(self):
        s = ServiceMultiplexor.get().get_one(platform_select(
            debian='supervisor',
            centos='supervisord',
        ))
        if not s.running:
            s.start()
        else:
            subprocess.call(['supervisorctl', 'reload'])
