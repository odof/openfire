# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from odoo import api, fields, models


class OFCalculationHeatLossLine(models.Model):
    _name = 'of.calculation.heat.loss.line'
    _description = u"Appareils compatibles pour la déperdition de chaleur"

    calculation_heat_loss_id = fields.Many2one(
        comodel_name='of.calculation.heat.loss', string=u"Calcul de déperdition de chaleur")
    product_id = fields.Many2one(comodel_name='product.template', string=u"Article", store=True)
    brand_name = fields.Many2one(
        comodel_name='of.product.brand', string=u"Marque", related='product_id.brand_id', store=True)
    list_price = fields.Float(string=u"Prix de vente", related="product_id.list_price")
    power_char = fields.Char(string=u"Puissance nominale", related="product_id.of_puissance_nom", store=True)
    power = fields.Float(string=u"Puissance nominale", compute='_compute_power')
    to_print = fields.Boolean(string=u"Impression", help=u"Activer / Désactiver l'impression")

    @api.depends('power_char')
    def _compute_power(self):
        for line in self:
            try:
                # Extract float from string
                line.power = re.findall(r"[-+]?(?:\d*\.*\d+)", line.power_char.replace(',','.'))[0]
            except ValueError:
                line.power = 0.0
