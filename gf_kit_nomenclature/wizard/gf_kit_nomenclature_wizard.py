# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError

class GFNomenclatureInsert(models.TransientModel):
    _inherit = "gf.nomenclature.insert"

    comp_ids = fields.One2many("gf.nomenclature.insert.kit.line", "nom_insert_id", string="Comps")

class GFNomenclatureInsertLine(models.TransientModel):
    _inherit = "gf.nomenclature.insert.line"

    kit_id = fields.Many2one("gf.nomenclature.insert.kit", string="Composants")

class GFNomenclatureKit(models.Model):
    _name = "gf.nomenclature.insert.kit"

    nom_insert_line_id = fields.Many2one("gf.nomenclature.insert.line", "Bill of Products", ondelete="cascade")
    name = fields.Char(string='Name', required=True, default="draft bill of products kit")
    kit_line_ids = fields.One2many('nomenclature.insert', 'kit_id', string="Components")

    qty_nom_insert_line = fields.Float(string="BoP Qty", related="nom_insert_line_id.product_qty", readonly=True)
    currency_id = fields.Many2one(related='nom_insert_line_id.currency_id', store=True, string='Currency', readonly=True)
    price_comps = fields.Monetary('Compo Price/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
                            help="Sum of the prices of all components necessary for 1 unit of this kit")
    cost_comps = fields.Monetary('Compo Cost/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
                                  help="Sum of the costs of all components necessary for 1 unit of this kit")

    of_pricing = fields.Selection([
        ('fixed', 'Fixed'),
        ('computed', 'Computed')
        ], string="Pricing", required=True, default='fixed',
            help="This field represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'computed', the price will be computed according to the components of the kit.")

    @api.multi
    @api.depends('kit_line_ids')
    def _compute_price_comps(self):
        for kit in self:
            price = 0.0
            cost = 0.0
            if kit.kit_line_ids:
                for comp in kit.kit_line_ids:
                    price += comp.price_unit * comp.qty_per_kit
                    cost += comp.cost_unit * comp.qty_per_kit
                kit.price_comps = price
                kit.cost_comps = cost


class GFNomenclatureKitLine(models.Model):
    _name = "gf.nomenclature.insert.kit.line"
    _order = "kit_id, sequence"

    kit_id = fields.Many2one('of.invoice.kit', string="Kit", ondelete="cascade")
    nom_insert_id = fields.Many2one("gf.nomenclature.insert", string="Bill of Products", related="kit_id.nom_insert_line_id.invoice_id")

    name = fields.Char(string='Name', required=True)
    default_code = fields.Char(string='Prod ref')
    sequence = fields.Integer(string=u'Sequence', default=10)

    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('of_is_kit', '=', False)]")
    currency_id = fields.Many2one(related='invoice_id.currency_id', store=True, string='Currency', readonly=True)
    product_uom_id = fields.Many2one('product.uom', string='UoM', required=True)
    price_unit = fields.Monetary('Unit Price', digits=dp.get_precision('Product Price'), required=True,default=0.0, oldname="unit_price")
    cost_unit = fields.Monetary('Unit Cost', digits=dp.get_precision('Product Price'))
    cost_total = fields.Monetary(string='Subtotal Cost', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
                            help="Cost of this component total quantity. Equal to total quantity * unit cost.")
    cost_per_kit = fields.Monetary(string='Cost/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
                            help="Cost of this component quantity necessary to make one unit of its invoice line kit. Equal to quantity per kit unit * unit cost.")

    qty_per_kit = fields.Float(string='Qty / Kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
                            help="Quantity per kit unit (invoice line).\n\
                        example: 2 kit K1 -> 3 prod P. \nP.qty_per_kit = 3\nP.qty_total = 6")

    nb_kits = fields.Float(string='Number of kits', related='kit_id.qty_invoice_line', readonly=True)
    qty_total = fields.Float(string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty_total', 
                                   help='total quantity equal to quantity per kit times number of kits.')
    #display_qty_changed = fields.Boolean(string="display qty changed message", default=False)
    price_total = fields.Monetary(string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
                            help="Price of this component total quantity. Equal to total quantity * unit price.")
    price_per_kit = fields.Monetary(string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
                            help="Price of this component quantity necessary to make one unit of its invoice line kit. Equal to quantity per kit unit * unit price.")
    kit_pricing = fields.Selection(related="kit_id.of_pricing", readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        #@TODO: handle case product is a kit (domain, error or load components
        if self.product_id:
            new_vals = {
                'name': self.product_id.name_get()[0][1] or self.product_id.name,
                'default_code': self.product_id.default_code,
                'product_uom_id': self.product_id.product_tmpl_id.uom_id,
                'price_unit': self.product_id.list_price,
                'cost_unit': self.product_id.standard_price,
            }
            if self.kit_id.invoice_line_id:
                if self.kit_id.invoice_line_id.of_pricing == 'fixed':
                    hide_prices = True
                else:
                    hide_prices = False
            else:
                hide_prices = self.hide_prices or False
            new_vals['hide_prices'] = hide_prices

            self.update(new_vals)

    @api.depends('price_unit', 'cost_unit', 'qty_per_kit', 'nb_kits')
    def _compute_prices(self):
        for comp in self:
            qty_per_kit = comp.qty_per_kit
            # prices
            comp.price_per_kit = comp.price_unit * qty_per_kit
            comp.price_total = comp.price_unit * qty_per_kit * comp.nb_kits
            # costs
            comp.cost_per_kit = comp.cost_unit * qty_per_kit
            comp.cost_total = comp.cost_unit * qty_per_kit * comp.nb_kits

    @api.depends('qty_per_kit', 'nb_kits')
    def _compute_qty_total(self):
        for comp in self:
            comp.qty_total = comp.qty_per_kit * comp.nb_kits 


