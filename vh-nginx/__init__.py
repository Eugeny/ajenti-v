import ajenti
from ajenti.api import *
from ajenti.plugins import *


info = PluginInfo(
    title='Ajenti VH - NGINX Support',
    icon='globe',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('services'),
        BinaryDependency('nginx'),
    ],
)


def init():
    import nginx
    import nginx_templates

    from ajenti.plugins import manager
    from ajenti.plugins.nginx.main import Nginx
    #from ajenti.plugins.apache.main import Apache
    manager.blacklist.append(Nginx)
    #manager.blacklist.append(Apache)