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
    import extensions
    import main