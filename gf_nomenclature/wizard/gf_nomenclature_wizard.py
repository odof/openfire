# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError

class GFNomenclatureInsert(models.TransientModel):
    """
wizard pour insérer une nomenclature
utiliser le même wizard pour lancer des appros depuis une nomenclature?
    """
    _name = "gf.nomenclature.insert"

    nomenclature_id = fields.Many2one("gf.nomenclature", string="Nomenclature", required=True)
    nom_insert_line_ids = fields.One2many("gf.nomenclature.insert.line", "nom_insert_id", string="Lignes")
    price_comps = fields.Monetary('Compo Price/Kit', digits=dp.get_precision('Product Price'), compute='_compute_compo_price_n_cost',
                                  help="Sum of the prices of all components necessary for 1 unit of this nom")
    cost_comps = fields.Monetary('Compo Cost/Kit', digits=dp.get_precision('Product Price'), compute='_compute_compo_price_n_cost',
                                  help="Sum of the costs of all components necessary for 1 unit of this nom")
    active = fields.Boolean(string="Active", default=True)
    product_count = fields.Integer('# Products', compute='_compute_product_count')
    sequence = fields.Integer(string=u'Sequence', default=10)
    currency_id = fields.Many2one(related="nomenclature_id.currency_id", readonly=True)

    @api.multi
    @api.depends('nom_insert_line_ids')
    def _compute_compo_price_n_cost(self):
        for nomenclature in self:
            price_n_cost = nomenclature.get_compo_price_n_cost()
            nomenclature.price_comps = price_n_cost['price']
            nomenclature.cost_comps = price_n_cost['cost']

    @api.multi
    @api.depends('nom_insert_line_ids')
    def _compute_product_count(self):
        for nomenclature in self:
            nomenclature.product_count = len(nomenclature.nom_insert_line_ids)

    @api.onchange("nomenclature_id")
    def _onchange_nomenclature_id(self):
        self.ensure_one()
        lines = [(5,)]
        if self.nomenclature_id:
            # charger les lignes
            for line in self.nomenclature_id.nom_insert_line_ids:
                vals = line._prepare_vals_for_insert()
                lines.append((0, 0, vals))

    def button_insert(self):
        # TODO: prendre le contenu des lignes
        lines_to_insert = []
        return_vals = {
            'nomenclature_id': self.nomenclature_id.id
        }
        if self._context.get('type') == 'sale':
            for line in self.nom_insert_line_ids:
                vals = line._prepare_vals_for_insert('sale')
                lines_to_insert.append((0, 0, vals))
            return_vals["order_line"] = lines_to_insert
            self.env["sale.order"].search([("id", "=", self._context.get("active_id"))]).write(return_vals)
        else:
            for line in self.nom_insert_line_ids:
                vals = line._prepare_vals_for_insert('account')
                lines_to_insert.append((0, 0, vals))
            return_vals["invoice_line_ids"] = lines_to_insert
            self.env["account.invoice"].search([("id", "=", self._context.get("active_id"))]).write(return_vals)

        return {'type': 'ir.actions.act_window_close'}

class GFNomenclatureInsertLine(models.TransientModel):
    """
wizard imitant les lignes de nomenclatures -> pour pouvoir en supprimer sans les supprimer de la nomenclature source
    """
    _name = "gf.nomenclature.insert.line"
    _order = 'nomenclature_id, sequence'

    def _get_default_product_uom_id(self):
        return self.env['product.uom'].search([], limit=1, order='id').id

    nom_insert_id = fields.Many2one("gf.nomenclature.insert", string="Nomenclature", required=True,
                             help="Nomenclature", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True,
                                 help="Product this line references")
    product_qty = fields.Float(string='Qty / Kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
                               help="Quantity per kit unit.")
    product_uom_id = fields.Many2one('product.uom', string='UoM', default=_get_default_product_uom_id, required=True, oldname="product_uom")
    sequence = fields.Integer(string=u'Sequence', default=10)
    product_price = fields.Float(related='product_id.list_price', readonly=True)
    product_cost = fields.Float(related='product_id.standard_price', readonly=True)
    currency_id = fields.Many2one(related="nom_insert_id.currency_id", readonly=True)

    def _prepare_vals_for_insert(self, type='sale'):
        self.ensure_one()
        if type == 'sale':
            vals = {
                'product_id': self.product_id.id,
                'product_uom_qty': self.product_qty,
                'product_uom': self.product_uom_id.id,
                'price_unit': self.product_price,
            }
        else:
            vals = {
                'product_id': self.product_id.id,
                'quantity': self.product_qty,
                'uom_id': self.product_uom_id.id,
                'price_unit': self.product_price,
            }
        return vals
