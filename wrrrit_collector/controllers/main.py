
from odoo import http


class WrrritCollector(http.Controller):
    @http.route('/wrrrit_collector/wrrrit_collector/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/wrrrit_collector/wrrrit_collector/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('wrrrit_collector.listing', {
            'root': '/wrrrit_collector/wrrrit_collector',
            'objects': http.request.env['wrrrit.collector.data'].search([]),
        })

    @http.route('/wrrrit_collector/wrrrit_collector/objects/<model("wrrrit.collector.data"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('wrrrit_collector.object', {
            'object': obj
        })
