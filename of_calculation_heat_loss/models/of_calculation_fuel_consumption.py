# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import openerp.addons.decimal_precision as dp


class OFCalculationFuelConsumption(models.Model):
    _name = 'of.calculation.fuel.consumption'
    _description = u"Consommation par combustible"

    calculation_id = fields.Many2one(
        comodel_name='of.calculation.heat.loss', string=u"Calcul de déperdition de chaleur", ondelete='cascade')
    fuel_id = fields.Many2one(comodel_name='of.calculation.fuel', string=u"Combustible", ondelete='cascade')
    uom_id = fields.Many2one(comodel_name='product.uom', string=u"Unité", related='fuel_id.uom_id')
    fuel_volume = fields.Float(string=u"Volume nécessaire", digits=(12, 2))
    fuel_cost = fields.Float(string=u"Coût annuel en €", digits=dp.get_precision('Product Price'))
