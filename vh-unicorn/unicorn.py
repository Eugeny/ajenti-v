import os
import shutil

from ajenti.api import *
from ajenti.plugins.vh.api import ApplicationGatewayComponent
from ajenti.plugins.vh.processes import SupervisorRestartable
from ajenti.util import platform_select

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


TEMPLATE_PROCESS = """
worker_processes %(workers)s
working_directory "%(root)s"
listen "unix:/var/run/ajenti-v-unicorn-%(id)s.sock", :backlog => 64
preload_app true

stderr_path "/var/log/unicorn/%(id)s.stderr.log"
stdout_path "/var/log/unicorn/%(id)s.stderr.log"

before_fork do |server, worker|
  defined?(ActiveRecord::Base) and
    ActiveRecord::Base.connection.disconnect!
end

after_fork do |server, worker|
  defined?(ActiveRecord::Base) and
    ActiveRecord::Base.establish_connection
end
"""


@plugin
class Gunicorn (ApplicationGatewayComponent):
    id = 'ruby-unicorn'
    title = 'Ruby Unicorn'

    def init(self):
        self.config_dir = '/etc/unicorn.d'

    def __generate_website(self, website):
        for location in website.locations:
            if location.backend.type == 'ruby-unicorn':
                c = TEMPLATE_PROCESS % {
                    'id': location.backend.id,
                    'workers': location.backend.params.get('workers', 4),
                    'root': website.root,
                }
                open(os.path.join(self.config_dir, location.backend.id + '.rb'), 'w').write(c)

    def create_configuration(self, config):
        if os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)
        os.mkdir(self.config_dir, 0755)

        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()
        for p in sup.tree.programs:
            if p.command and p.command.startswith('unicorn'):
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                for location in website.locations:
                    if location.backend.type == 'ruby-unicorn':
                        self.__generate_website(website)
                        p = ProgramData()
                        p.name = location.backend.id
                        p.command = 'unicorn_rails -E production -c %s/%s.rb' % (self.config_dir, location.backend.id)
                        sup.tree.programs.append(p)

        sup.save()

    def apply_configuration(self):
        log_dir = '/var/log/unicorn'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, 0755)

        SupervisorRestartable.get().schedule()
