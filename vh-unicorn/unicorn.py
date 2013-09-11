import os
import shutil
import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import ApplicationGatewayComponent

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


TEMPLATE_PROCESS = """
worker_processes %(workers)s
working_directory "%(root)s"
listen "unix:/var/run/unicorn-%(id)s.sock", :backlog => 64
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
        i = 0
        for location in website.locations:
            if location.backend.type == 'ruby-unicorn':
                i += 1
                location.backend.id = website.slug + '-ruby-unicorn-' + str(i)
                c = TEMPLATE_PROCESS % {
                    'id': location.backend.id,
                    'workers': location.backend.params.get('workers', 4),
                    'root': website.root,
                }
                open(os.path.join(self.config_dir, location.backend.id + '.rb'), 'w').write(c)

    def create_configuration(self, config):
        if os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)
        os.mkdir(self.config_dir)

        sup = SupervisorConfig(path='/etc/supervisor/supervisord.conf')
        sup.load()
        for p in sup.tree.programs:
            if p.command.startswith('unicorn'):
                sup.tree.programs.remove(p)

        for website in config.websites:
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
            os.makedirs(log_dir)

        s = ServiceMultiplexor.get().get_one('unicorn')
        if not s.running:
            s.start()
        else:
            s.command('reload')

        s = ServiceMultiplexor.get().get_one('supervisor')
        if not s.running:
            s.start()
        else:
            subprocess.call(['supervisorctl', 'reload'])
