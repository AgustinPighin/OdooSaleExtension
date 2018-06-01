from openerp import models, fields, api
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import time
# from openerp.exceptions import Warning
#mport openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    
    _inherit = 'sale.order'
    price_default = fields.Float( string='Precio Default', default=9 )

class SaleOrderLine(models.Model):
    
    _inherit = 'sale.order.line'

    last_seller_price = fields.Float( string='Costo Probable', compute='_get_last_seller_price' )
    last_seller_date  = fields.Date('Fecha Ultimo Precio Proveedor')
    last_seller_brand = fields.Char('Vendor Product Name')

    product_seller_ids = fields.Many2many('product.supplierinfo', string='Seller Id', compute="_get_sellers_id", readonly=False, copy=False)
    
    product_customer_invoice_lines = fields.Many2many('account.invoice.line', string='Last Customer Invoice Lines for Product', compute="_get_customer_invoice_lines", readonly=False, copy=False)
    
    product_vendor_invoice_lines = fields.Many2many('account.invoice.line', string='Last Vendor Invoice Lines for Product', compute="_get_vendor_invoice_lines", readonly=False, copy=False)
    

    @api.multi
    @api.onchange('product_id')
    def _get_sellers_id(self):
        for line in self:
            if line.product_tmpl_id:
                domain = [  ('product_tmpl_id', '=', line.product_tmpl_id.id ),
                            ('date_end'  , '!=', False  )  ]
                sellers = self.env['product.supplierinfo'].search(domain)
                if sellers:
                    line.product_seller_ids = sellers

    @api.multi
    @api.onchange('product_id')
    def _get_customer_invoice_lines(self):
        for line in self:
            if line.product_id:
            
                domain = [  ('invoice_id.partner_id', '=', line.order_partner_id.id ),
                            ('product_id', '=', line.product_id.id ),
                            ('invoice_id.type', '=', 'out_invoice' ),
                            ('invoice_id.state', 'not in', ('cancel', 'draft') )  ]

                line.product_customer_invoice_lines = self.env['account.invoice.line'].search(domain)

    @api.multi
    @api.onchange('product_id')
    def _get_vendor_invoice_lines(self):
        for line in self:
            if line.product_id:
                domain = [  ('product_id', '=', line.product_id.id ),
                            ('invoice_id.type', '=', 'in_invoice' ),
                            ('invoice_id.state', 'not in', ('cancel', 'draft') )  ]

                line.product_vendor_invoice_lines = self.env['account.invoice.line'].search(domain)

    @api.multi
    @api.onchange('product_id','product_qty')
    def _get_last_seller_price(self):
        for line in self:
            if line.product_tmpl_id:
                qty         = line.product_qty
                date_order  = line.order_id.date_order
                product_uom = line.product_uom
                seller      = line.product_tmpl_id._select_sale_seller( quantity=qty, date=date_order and date_order[:10], uom_id=product_uom )
                if seller:
                    _logger.info("TESTAGU-SaleItem-Seller Found %s" % (seller.id))
#                     = datetime.date.today()
                    today = datetime.now().strftime('%Y-%m-%d')
                    _logger.info('TESTAGU-SaleItem-Fecha de hoy %s' % (today))
                    monthago = datetime.strptime( today, '%Y-%m-%d') - relativedelta(days=30)
                    _logger.info('TESTAGU-SaleItem-Fecha de hace un mes %s' % (monthago))
                    _logger.info('TESTAGU-SaleItem-Fecha de linea %s' % (seller.date_end))

                    if seller.date_end == False:
                        continue
#                    today = datetime.today(),DF)
                    if seller.date_end and seller.date_end < today:
                        _logger.info('TESTAGU-SaleItem-dateend<today %s < %s' % (seller.date_end,today))
                        line.last_seller_brand = ' '
                        line.last_seller_price = 0.0
                        line.last_seller_date  = False
                    elif seller.date_end and today < seller.date_end:
                        _logger.info('TESTAGU-SaleItem-today %s <date_end%s  < ' % (today,seller.date_end))
                        line.last_seller_brand = seller.product_name
                        line.last_seller_price = seller.price
                        line.last_seller_date  = seller.date_start
                    else:
                         _logger.info('TESTAGU-SaleItem-No fue nada juez')
class ResPartner(models.Model):
    _inherit = 'res.partner'

    price_validity_dates = fields.Integer(
        string='Price Validity Days',
        default=10
    )

class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'    
    
    @api.onchange('name','date_start')
    def _get_sale_dates(self):
        
        _logger.info('**************** API ON CHANGE TRIGGERED ********************' )
        if not self.name:
            return

        if self.name.price_validity_dates:
            days_validity = self.name.price_validity_dates
        else:
            days_validity = 15

        _logger.info('TESTAGU-: 2.3 Cantidad de dias %s ' % (days_validity) )

        if  self.date_start and self.date_end: 

            next_date = self.date_end
            _logger.info('TESTAGU-: 1 Existe start %s Next %s ' % (self.date_start,next_date) )

        elif  self.date_start and not self.date_end:
            _logger.info('TESTAGU-: 2.1 No existe date next. Date Start: %s ' % (self.date_start) )    
            today = datetime.strptime(self.date_start, DATE_FORMAT).date()
            _logger.info('TESTAGU-: 2.2 Date stat convertido a today %s ' % (today) )    
            
            self.date_end = today + relativedelta(days=days_validity )
            _logger.info('TESTAGU-: 2.4 Nuevo next_date %s ' % (self.date_end) )
        else:
            
            today = date.today()
            next_date = today + relativedelta( days=days_validity )
            _logger.info('TESTAGU-: 3  Today %s Next %s ' % (today,next_date) )
            self.date_start = today
            self.date_end   = next_date

class ProductTemplate(models.Model):

    _inherit = 'product.template'

    @api.multi
    def _select_sale_seller(self, quantity=0.0,
                       date=time.strftime(DATE_FORMAT),
                       uom_id=False):
        # this method is copied from the standard _select_seller on the
        # product.product model
        self.ensure_one()
        res = self.env['product.supplierinfo'].browse([])
        for seller in self.seller_ids:
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_qty_obj(
                    uom_id, quantity_uom_seller, seller.product_uom)
            if seller.date_start and seller.date_start > date:
                _logger.info("TESTAGU-ProdTemplate-date_start > date")
                continue
            if seller.date_end   and seller.date_end < date:
                _logger.info("TESTAGU-ProdTemplate-date_end < date")
                continue
            if quantity_uom_seller < seller.qty:
                continue
            if seller.product_tmpl_id and seller.product_tmpl_id != self:
                continue
            _logger.info("TESTAGU-ProdTemplate-SellerFound:%s,fechaS %s" % ( seller.id, seller.date_end ) )
            res |= seller
            break
        return res

    @api.multi
    def _get_sale_sellers(self):
        
        self.ensure_one()

        domain = [  ('invoice_id.partner_id', '=', line.order_partner_id.id ),
                    ('invoice_id.state', 'not in', ('cancel', 'draft') ),
                    ('product_id', '=', line.product_id.id )  ]


        res = self.env['product.supplierinfo'].browse([])
        if self.seller_ids:
            
            return self.seller_ids



class ProductProduct(models.Model):
    
    _inherit = 'product.product'
    
#    def _select_sale_seller(self, quantity=0.0, date=time.strftime(DF), uom_id=False):
    def _select_sale_seller(self):
        # this method is copied from the standard _select_seller on the
        # product.product model
        self.ensure_one()
        res = self.env['product.supplierinfo'].browse([])
        for seller in self.seller_ids:
#            quantity_uom_seller = quantity
#            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
#                quantity_uom_seller = uom_id._compute_qty_obj(
#                    uom_id, quantity_uom_seller, seller.product_uom)
#            if seller.date_start and seller.date_start > date:
#                continue
#            if seller.date_end and seller.date_end < date:
#                continue
#            if partner_id and seller.name not in [partner_id,
#                                                  partner_id.parent_id]:
#                continue
#            if quantity_uom_seller < seller.qty:
#                continue
#            if seller.product_tmpl_id and seller.product_tmpl_id != self:
#               continue

            res |= seller
            break
        return res

