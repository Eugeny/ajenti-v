import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import ApplicationGatewayComponent
from ajenti.util import platform_select

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


@plugin
class NodeJS (ApplicationGatewayComponent):
    id = 'nodejs'
    title = 'Node.JS'

    def create_configuration(self, config):
        node_bin = 'node'
        try:
            subprocess.call(['which', 'node'])
        except:
            node_bin = 'nodejs'

        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()
        for p in sup.tree.programs:
            if p.command and p.command.startswith('node '):
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                i = 0
                for location in website.locations:
                    if location.backend.type == 'nodejs':
                        i += 1
                        location.backend.id = \
                            website.slug + '-nodejs-' + str(i)
                        p = ProgramData()
                        p.name = location.backend.id
                        p.command = '%s %s' % (
                            node_bin,
                            location.backend.params.get('script', None) or '.'
                        )
                        p.directory = location.path or website.root
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
