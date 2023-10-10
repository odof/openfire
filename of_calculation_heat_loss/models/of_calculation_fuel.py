# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import openerp.addons.decimal_precision as dp


class OFCalculationFuel(models.Model):
    _name = 'of.calculation.fuel'
    _description = u"Combustible"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    calorific_value = fields.Float(
        string=u"Pouvoir calorifique", help=u"En kWh par unité de mesure",
        digits=dp.get_precision('Product Unit of Measure'))
    price = fields.Float(string=u"Prix", help=u"En € par unité de mesure", digits=(12, 6))
    uom_id = fields.Many2one(comodel_name='product.uom', string=u"Unité")
