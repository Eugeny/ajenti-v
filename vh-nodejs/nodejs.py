import subprocess

from ajenti.api import *
from ajenti.util import platform_select

from ajenti.plugins.supervisor.client import SupervisorServiceManager
from ajenti.plugins.vh.api import ApplicationGatewayComponent, SanityCheck
from ajenti.plugins.vh.processes import SupervisorRestartable

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


class NodeServerTest (SanityCheck):
    def __init__(self, backend):
        SanityCheck.__init__(self)
        self.backend = backend
        self.type = _('Node.js service')
        self.name = backend.id

    def check(self):
        s = SupervisorServiceManager.get().get_one(self.backend.id)
        if s:
            self.message = s.status
        return s and s.running


@plugin
class NodeJS (ApplicationGatewayComponent):
    id = 'nodejs'
    title = 'Node.JS'

    def init(self):
        self.checks = []

    def create_configuration(self, config):
        self.checks = []

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
                for location in website.locations:
                    if location.backend.type == 'nodejs':
                        self.checks.append(NodeServerTest(location.backend))
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
        SupervisorRestartable.get().schedule()

    def get_checks(self):
        return self.checks
