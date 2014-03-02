from ajenti.api import *
from ajenti.plugins import *

info = PluginInfo(
    title='Ajenti V Mail',
    icon='envelope',
    dependencies=[
        PluginDependency('vh'),
        PluginDependency('main'),
        PluginDependency('services'),
    ],
)

def init():
    import api
    import main
