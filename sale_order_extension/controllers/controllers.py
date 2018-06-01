# -*- coding: utf-8 -*-
from openerp import http

# class SaleOrderExtension(http.Controller):
#     @http.route('/sale_order_extension/sale_order_extension/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_order_extension/sale_order_extension/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_order_extension.listing', {
#             'root': '/sale_order_extension/sale_order_extension',
#             'objects': http.request.env['sale_order_extension.sale_order_extension'].search([]),
#         })

#     @http.route('/sale_order_extension/sale_order_extension/objects/<model("sale_order_extension.sale_order_extension"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_order_extension.object', {
#             'object': obj
#         })