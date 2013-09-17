from ajenti.api import plugin
from ajenti.plugins.vh.api import ApplicationGatewayComponent


@plugin
class ProxyPass (ApplicationGatewayComponent):
    id = 'proxy'
    title = _('Reverse proxy')