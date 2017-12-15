# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError

class GFNomenclature(models.Model):
    _inherit = "gf.nomenclature"

    kit_count = fields.Integer(string='# Kits', compute='_compute_product_count')
    comp_count = fields.Integer(string='# Comps', compute='_compute_product_count')
    contains_kit = fields.Boolean(string='Contains a kit', compute='_compute_product_count')

    @api.multi
    @api.depends('nom_line_ids')
    def _compute_product_count(self):
        """
redef fonction parente prise en compte des kits
        """
        for nomenclature in self:
            comp_count = 0
            kit_count = 0
            for nom_line in nomenclature.nom_line_ids:
                if nom_line.kit_line_ids != []:
                    kit_count += 1
                    comp_count += len(nom_line.kit_line_ids)
            nomenclature.product_count = len(nomenclature.nom_line_ids)
            nomenclature.kit_count = kit_count
            nomenclature.comp_count = comp_count
            nomenclature.contains_kit = kit_count > 0

    def get_compo_price_n_cost(self):
        """
redef fonction parente prise en compte des kits
        """
        self.ensure_one()
        res = {'price': 0.0, 'cost': 0.0}
        for line in self.nom_line_ids:
            if line.product_id.product_tmpl_id.of_is_kit:
                res['price'] += line.product_id.of_price_used * line.product_qty
                res['cost'] += line.product_id.cost_comps * line.product_qty
            else:
                res['price'] += line.product_id.list_price * line.product_qty
                res['cost'] += line.product_id.standard_price * line.product_qty
        return res

class GFNomenclatureLine(models.Model):
    _name = "gf.nomenclature.line"
    _order = 'nomenclature_id, sequence'

    kit_line_ids = fields.One2many(related="product_id.product_tmpl_id.kit_line_ids", readonly=True)  #probleme de onchange O2M dans O2M malgré readonly?

    def _prepare_vals_for_insert(self):
        self.ensure_one()
        vals = {
            'product_id': self.product_id.id,
            'product_qty': self.product_qty,
            'product_uom_id': self.product_uom_id.id,
            'sequence': self.sequence,
        }
        if self.kit_line_ids != []:
            #TODO creer une instance "gf.nomenclature.insert.kit"
        return vals
