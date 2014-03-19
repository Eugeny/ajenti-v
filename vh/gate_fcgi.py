from ajenti.api import plugin
from ajenti.plugins.vh.api import ApplicationGatewayComponent


@plugin
class FCGIPass (ApplicationGatewayComponent):
    id = 'fcgi'
    title = _('Custom FCGI')