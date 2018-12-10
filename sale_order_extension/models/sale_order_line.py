from openerp import models, fields, api
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import date, datetime
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta
import time
# from openerp.exceptions import Warning
#mport openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    
    _inherit = 'sale.order'
    total_cost = fields.Monetary(string='Costo Total', store=True, readonly=True, compute='_calcular_costo_total')
    compute_disabled = fields.Boolean(string='Desabilitar calculo precios', help="Marcar para desabilitar el calculo de precios y mejorar la performance", default=False)

    price_default = fields.Float( string='Precio Default', default=9 )
    rentabilidad_default = fields.Float(string='Rentabilidad Default', digits=dp.get_precision('Discount'), default=20.0 )

    @api.depends('order_line.cost_subtotal')
    def _calcular_costo_total(self):
        """
        Compute the total cost of the SO
        """
        for order in self:
            costo_total = 0.0
            for line in order.order_line:
                costo_total += line.cost_subtotal

            order.update({
                'total_cost': costo_total,
            })


    @api.multi
    def compute_rentabilidad(self):
        _logger.info("1.1-TESTAGU-SaleOrder-Compute Rentabilidad")

        for line in self.order_line:
            if line.product_tmpl_id:
                _logger.info("1.1-TESTAGU-SALE HEADER-Compute Rentabilidad -> Product ID: %s" % (line.product_tmpl_id))
                line.rentabilidad = self.rentabilidad_default

        _logger.info("1.3-TESTAGU-SALE HEADER-Compute Rentabilidad-Cost Subtotal")
        self.order_line._update_cost_subtotal()

        _logger.info("1.4-TESTAGU-SALE HEADER-Compute Rentabilidad-Update Margin extended")
        self.order_line._update_margin_extended()

    @api.multi
    def recalculate_purchase_price(self):

        _logger.info("2.1-TESTAGU-SALE HEADER-Recalcular last seller price.")
        
        self.order_line._get_last_seller_price()
        self.order_line._update_cost_subtotal()
        self.order_line._update_margin_extended()

    @api.multi
    def calculate_item_history(self):
        _logger.info("3.1-TESTAGU-SALE HEADER-Recalcular item history")
        self.order_line.get_history_seller_price()
#        self.order_line.get_history_vendor_invoice()
        self.order_line.get_history_customer_invoice()



class SaleOrderLine(models.Model):
    
    _inherit = 'sale.order.line'

    last_seller_price = fields.Float( string='Costo Probable', store="True")
    last_seller_date  = fields.Date('Inicio Validez',store="True" )
    last_seller_brand = fields.Char('Marca Proveedor',store="True" )
    last_seller_id    = fields.Many2one('product.supplierinfo', string='Seller Id', readonly=True, copy=False)

    rentabilidad  = fields.Float(string='Rentabilidad (%)', store="True", digits=dp.get_precision('Discount'),default=20.0)
    cost_subtotal = fields.Monetary(string='Costo Subtotal',store="True")
   
    product_seller_ids              = fields.Many2many('product.supplierinfo', string='Seller Id', readonly=False, copy=False)
    product_customer_invoice_lines  = fields.Many2many('account.invoice.line', string='Last Customer Invoice Lines for Product', readonly=False, copy=False)
    product_vendor_invoice_lines    = fields.Many2many('account.invoice.line', string='Last Vendor Invoice Lines for Product',  readonly=False, copy=False)
    

    @api.multi
    def get_history_seller_price(self):

        for line in self:
 
            if line.product_tmpl_id:

                line.product_seller_ids = self.env['product.supplierinfo'].search(
                    [  ('product_tmpl_id', '=', line.product_tmpl_id.id ),
                        ('date_end'  , '!=', False  )  ]
                )
    @api.multi
    def get_history_vendor_invoice(self):

        for line in self:
 
            if line.product_tmpl_id:

                line.product_vendor_invoice_lines = self.env['account.invoice.line'].search(
                    [  ('product_id', '=', line.product_id.id ),
                        ('invoice_id.type', '=', 'in_invoice' ),
                        ('invoice_id.state', 'not in', ('cancel', 'draft') )  ]
                )
    
    @api.multi
    def get_history_customer_invoice(self):

        for line in self:
 
            if line.product_tmpl_id:

                line.product_customer_invoice_lines = self.env['account.invoice.line'].search(
                    [   
                        #('invoice_id.partner_id', '=', line.order_partner_id.id ),
                        ('product_id', '=', line.product_id.id ),
                        ('invoice_id.type', '=', 'out_invoice' ),
                        ('invoice_id.state', 'not in', ('cancel', 'draft') )  ]
                )


    #@api.multi
    #@api.onchange('product_id')
    #def _get_sellers_id(self):
    #    for line in self:
    #        if line.product_tmpl_id:
    #            domain = [  ('product_tmpl_id', '=', line.product_tmpl_id.id ),
    #                        ('date_end'  , '!=', False  )  ]
    #            sellers = self.env['product.supplierinfo'].search(domain)
    #            if sellers:
    #                line.product_seller_ids = sellers 

    #@api.multi
    #@api.onchange('product_id')
    #def _get_customer_invoice_lines(self):
    #    for line in self:
    #        if line.product_id:
            
    #            domain = [  ('invoice_id.partner_id', '=', line.order_partner_id.id ),
    #                        ('product_id', '=', line.product_id.id ),
    #                        ('invoice_id.type', '=', 'out_invoice' ),
    #                        ('invoice_id.state', 'not in', ('cancel', 'draft') )  ]

    #            line.product_customer_invoice_lines = self.env['account.invoice.line'].search(domain)
    
    #@api.multi
    #@api.onchange('product_id')
    #def _get_vendor_invoice_lines(self):
    #    for line in self:
    #        if line.product_id:
    #            domain = [  ('product_id', '=', line.product_id.id ),
    #                        ('invoice_id.type', '=', 'in_invoice' ),
    #                        ('invoice_id.state', 'not in', ('cancel', 'draft') )  ]

    #            line.product_vendor_invoice_lines = self.env['account.invoice.line'].search(domain)


    @api.multi
    def _compute_rentabilidad(self):
        for line in self: 
            if line.product_tmpl_id:
                _logger.info('12.1 TESTAGU-compute_rentabilidad-SaleItem-Compute Rentabilidad LInea')
                if not line.rentabilidad:
                    line.rentabilidad = line.order_id.rentabilidad_default


    @api.onchange('product_id', 'product_uom')
    def product_id_change_margin(self):
        _logger.info('2.1 Sobreescritura del product_id_change_margin')
        return

    @api.depends('product_uom_qty','price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """

        for line in self:
            
            if not line.order_id.compute_disabled:
           
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                _logger.info('15.1 Sobreescritura del _compute_amount Price %s' % (price) )
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
                _logger.info('15.2 Sobreescritura del _compute_amount Taxes%s' % (taxes) )
                line.update({
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })

            else:

                _logger.info('15.3 Compute disabled %' )

                return

    @api.depends('price_subtotal', 'product_uom_qty')
    def _get_price_reduce(self):
        _logger.info('11.1 TESTAGU-_get_price_reduce-SaleItem-price_subtotalproduct_uom_qty')
        for line in self:
            if not line.order_id.compute_disabled:
                _logger.info('11.1 TESTAGU-_get_price_reduce-SaleItem-price_subtotal %s Price unit %s ' % ( line.price_subtotal, line.price_unit))
                line.price_reduce = line.price_subtotal / line.product_uom_qty if line.product_uom_qty else 0.0
            else:              
                _logger.info('15.3 Compute disabled' )
                return

    @api.multi
    @api.onchange('rentabilidad')
    def update_price_unit(self):
        
        _logger.info("1.1TESTAGU-SaleItem-update_price_unit-Update Price Unit Method")
        
        for line in self: 
            if line.product_tmpl_id:
                _logger.info('1.2 TESTAGU-SaleItem-Update Price-Price Unit %s' % (line.price_unit))
                _logger.info('1.3 TESTAGU-SaleItem-Update Price-Purchase Price %s' % (line.purchase_price))
                #if not line.rentabilidad:
                #    line.rentabilidad = line.order_id.rentabilidad_default
                line.price_unit = line.purchase_price * ( 1 + ( line.rentabilidad / 100 ) )
                _logger.info('1.4 TESTAGU-SaleItem-Update Price-Price Unit changed %s' % (line.price_unit))

    @api.multi
    @api.onchange('product_uom_qty','purchase_price','price_unit','rentabilidad')
    def _update_cost_subtotal(self):
        _logger.info('3.1 TESTAGU-SaleItem-Update Cost sutbtotal')
        for line in self:
            _logger.info('3.2 TESTAGU-SaleItem-Product %s' % ('product_id'))
            if line.product_tmpl_id:
                _logger.info('3.2.1 TESTAGU-SaleItem-Cost %s , qty %s ' % (line.purchase_price,line.product_uom_qty))
                line.cost_subtotal  = line.purchase_price * line.product_uom_qty
                line.price_unit     = line.purchase_price * ( 1 + ( line.rentabilidad / 100 ) )
                _logger.info('3.2.2 TESTAGU-SaleItem-Costo Subtotal (%s, %s) ' % (line.cost_subtotal,line.price_unit))

    @api.multi
    @api.onchange('cost_subtotal','price_subtotal')
    def _update_margin_extended(self):
        _logger.info('7.1 TESTAGU-Update margin Line')
        for line in self:
            _logger.info('7.2 TESTAGU-Update margin Line Product %s' % (line.product_id))
            _logger.info('7.2 TESTAGU-Update margin Line Product Price Subtotal %s Cost subtotal %s ' % (line.price_subtotal,line.cost_subtotal))
            line.margin = line.price_subtotal - line.cost_subtotal

    @api.model
    def _get_purchase_price(self, pricelist, product, product_uom, date):
        _logger.info('4.1 TESTAGU-Update purchase price')
        return {}                
 
    @api.multi
    @api.onchange('product_id','product_uom_qty')
    def _get_last_seller_price(self):

        _logger.info("2.1 LastSellerPrice-LAST SELLER METHOD CALL")

        todaynof = datetime.now()
        _logger.info('2.2 LastSellerPrice-Fecha de hoy sin formato es %s' % (todaynof))
        today = datetime.now().strftime('%Y-%m-%d')
        _logger.info('2.2 LastSellerPrice-Fecha de hoy formateada es %s' % (today))
        monthago = datetime.strptime( today, '%Y-%m-%d') - relativedelta(days=30)
        _logger.info('2.3 LastSellerPrice-Fecha de hace un mes %s' % (monthago))

        for line in self:
            
            if line.product_tmpl_id and line.state not in ('sale','done'):

                if line.order_id.compute_disabled:
                    return

                qty         = line.product_uom_qty
                _logger.info("***********************************")
                _logger.info('2.1,1 TESTAGU-SaleItem-Last Seller -> qty %s uom_qty %s' % (line.product_uom_qty,line.product_qty))
                _logger.info("***********************************")

                date_order  = line.order_id.date_order
                _logger.info('2.2 LastSellerPrice-Fecha de orden %s' % (date_order))
                product_uom = line.product_uom
                seller      = line.product_tmpl_id._select_sale_seller( quantity=qty, date=today and today[:10], uom_id=product_uom )
                
                if seller:

                    _logger.info('2.4 TESTAGU-SaleItem-Fecha de linea %s' % (seller.date_end))

                    if seller.date_end == False:
                        continue
#                    today = datetime.today(),DF)
                    if seller.date_end and seller.date_end < today:

                        _logger.info('2.5 TESTAGU-SaleItem-dateend<today %s < %s' % (seller.date_end,today))

                        line.last_seller_brand = ' '
                        line.last_seller_date  = False
                        line.last_seller_price = 0.0
                        line.purchase_price    = 0.0
                        line.last_seller_id    = False
                        line.price_unit        = 0.0

                    elif seller.date_end and today <= seller.date_end:
                        
                        _logger.info("2.6.1 TESTAGU-SaleItem-Seller Found %s" % (seller.id))
                        _logger.info('2.6.2 TESTAGU-SaleItem-Seller Found today %s <date_end%s ' % (today,seller.date_end))
                        _logger.info("2.6.3 TESTAGU-SaleItem-Product Name %s Date Start %s" % (seller.product_name,line.last_seller_date))
                        _logger.info('2.6.4 TESTAGU-SaleItem-Last Seller Price %s ' % (line.last_seller_price))
                        _logger.info('2.6.5 TESTAGU-SaleItem-Purchase Price %s' % (line.purchase_price))

                        line.last_seller_brand = seller.product_name
                        line.last_seller_date  = seller.date_start
                        line.last_seller_price = seller.price
                        line.purchase_price    = seller.price
                        line.last_seller_id    = seller.id
                        line.price_unit        = line.purchase_price * ( 1 + ( line.rentabilidad / 100 ) )

                        _logger.info('2.6.6 TESTAGU-SaleItem-Price Unit %s' % (line.price_unit))
                    else:
                         _logger.info('TESTAGU-SaleItem-No fue nada juez')

                else:

                    line.last_seller_brand = ' '
                    line.last_seller_date  = False
                    line.last_seller_price = 0.0
                    line.purchase_price    = 0.0
                    line.last_seller_id    = False
                    line.price_unit        = 0.0
                


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
        sellers = self.seller_ids.sorted( key = ( lambda x: x.date_end ) , reverse=True )
        
        for seller in sellers:
            _logger.info("TESTAGU-99.1ProdTemplate-Probando con Seller ID: %s " % (seller.name))
            quantity_uom_seller = quantity
            _logger.info("TESTAGU-99.2 ProdTemplate-Cantidad UOM SELLER: %s " % (quantity_uom_seller))
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                _logger.info("TESTAGU-99.2.1ProdTemplate-Cantidad UOM: %s " % (quantity_uom_seller))
                quantity_uom_seller = uom_id._compute_qty_obj(
                    uom_id, quantity_uom_seller, seller.product_uom)
            if seller.date_start and seller.date_start > date:
                _logger.info("TESTAGU-99.2.2-ProdTemplate-date_start > date")
                continue
            if seller.date_end   and seller.date_end < date:
                _logger.info("TESTAGU-99.2.3-ProdTemplate-date_end %s < date %s - Seller ID: %s " % (seller.date_end,date,seller.name))
                continue
            if quantity_uom_seller < seller.qty:
                _logger.info("TESTAGU-99.2.4-ProdTemplate-Cantidad UOM seller %s< seller quantity: %s " % (quantity_uom_seller,seller.qty))
                continue
            if seller.product_tmpl_id and seller.product_tmpl_id != self:
                continue
            _logger.info("TESTAGU-99.2.5-ProdTemplate-SellerFound!:%s,fechaS %s" % ( seller.id, seller.date_end ) )
            res |= seller
            break
        return  res

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

