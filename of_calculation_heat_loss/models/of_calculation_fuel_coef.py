# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
import odoo.addons.decimal_precision as dp


class OFCalculationFuelConsumption(models.Model):
    _name = 'of.calculation.fuel.coef'
    _description = u"Chauffage au bois (Coefficient d'utilisation)"

    name = fields.Char(string=u"Type de chauffage", required=True)
    coef = fields.Float(string=u"Coefficient", required=True)
