# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
import odoo.addons.decimal_precision as dp


class OFCalculationFuel(models.Model):
    _name = 'of.calculation.fuel'
    _description = u"Combustible"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    calorific_value = fields.Float(
        string=u"Pouvoir calorifique (kWh/unité)", help=u"En kWh par unité de mesure",
        digits=dp.get_precision('Product Unit of Measure'))
    price = fields.Float(string=u"Prix unitaire", help=u"En € par unité de mesure", digits=(12, 6))
    kwh_unit_price = fields.Float(string="Prix du kWh (€)", compute='_compute_kwh_unit_price', digits=(12, 6))
    uom_id = fields.Many2one(comodel_name='product.uom', string=u"Unité")

    def _compute_kwh_unit_price(self):
        for rec in self:
            rec.kwh_unit_price = rec.price / rec.calorific_value if rec.calorific_value else 0
