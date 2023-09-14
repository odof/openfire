# coding=utf-8

from odoo import api, fields, models


class OFCalculationHeatLossLine(models.Model):
    _name = 'of.calculation.heat.loss.line'
    _description = u"Appareils compatibles pour la déperdition de chaleur"

    calculation_heat_loss_id = fields.Many2one(
        comodel_name='of.calculation.heat.loss', string=u"Calcul de déperdition de chaleur")
    product_id = fields.Many2one(comodel_name='product.template', string=u"Article")
    brand_name = fields.Char(string=u"Marque", related='product_id.brand_id.name')
    list_price = fields.Float(string=u"Prix de vente", related="product_id.list_price")
    of_puissance_nom = fields.Char(string=u"Puissance nominale", related="product_id.of_puissance_nom")
    impression_dc = fields.Boolean(string=u"Impression", help=u"Activer / Désactiver l'impression")
