import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import ApplicationGatewayComponent

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


@plugin
class NodeJS (ApplicationGatewayComponent):
    id = 'nodejs'
    title = 'Node.JS'

    def create_configuration(self, config):
        sup = SupervisorConfig(path='/etc/supervisor/supervisord.conf')
        sup.load()
        for p in sup.tree.programs:
            if p.command.startswith('node '):
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                i = 0
                for location in website.locations:
                    if location.backend.type == 'nodejs':
                        i += 1
                        location.backend.id = website.slug + '-nodejs-' + str(i)
                        p = ProgramData()
                        p.name = location.backend.id
                        p.command = 'node %s' % location.backend.params.get('path', '/')
                        sup.tree.programs.append(p)

        sup.save()

    def apply_configuration(self):
        s = ServiceMultiplexor.get().get_one('supervisor')
        if not s.running:
            s.start()
        else:
            subprocess.call(['supervisorctl', 'reload'])
