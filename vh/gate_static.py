from ajenti.api import plugin
from ajenti.plugins.vh.api import ApplicationGatewayComponent


@plugin
class Static (ApplicationGatewayComponent):
    id = 'static'
    title = _('Static files')