import ajenti
from ajenti.api import *
from ajenti.plugins import *


ajenti.edition += '+vh'


info = PluginInfo(
    title='Ajenti VH Virtual Hosting',
    icon='globe',
    dependencies=[
        PluginDependency('main'),
        PluginDependency('services'),
        ModuleDependency('slugify'),
    ],
)


def init():
    import api
    import fcgi.phpfpm
    import webservers.nginx

    import main

    from ajenti.plugins import manager
    from ajenti.plugins.nginx.main import Nginx
    from ajenti.plugins.apache.main import Apache
    manager.blacklist.append(Nginx)
    manager.blacklist.append(Apache)