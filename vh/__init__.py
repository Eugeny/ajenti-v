import ajenti
from ajenti.api import *
from ajenti.plugins import *


ajenti.edition += '+vh'


info = PluginInfo(
    title='Ajenti V Virtual Hosting',
    icon='globe',
    dependencies=[
        PluginDependency('main'),
        PluginDependency('services'),
    ],
)

destroyed_configs = []

def init():
    import api
    import extensions
    import main
    import ipc

    import gate_static
    import gate_proxy
    import gate_fcgi