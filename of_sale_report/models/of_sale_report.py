# -*- coding: utf-8 -*-

from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_date_de_pose = fields.Date(u'Date de pose prévisionnelle')

class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_rapport_sur_mesure = fields.Selection(
        [('fabricant', "Rapports fabricant"),
         ('revendeur', "Rapports revendeur"),
         ('tous', "Tous les rapports")],
        string=u"(OF) Type de rapports", required=True, default='tous',
        help=u"Donne l'accès aux rapport sur mesure")

    @api.multi
    def set_of_rapport_sur_mesure_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_rapport_sur_mesure', self.of_rapport_sur_mesure)
