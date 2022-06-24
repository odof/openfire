# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_recalcul_pa = fields.Boolean(string=u"(OF) Recalcul auto des prix d'achats sur lignes de commande")

    @api.multi
    def set_of_recalcul_pa_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_recalcul_pa', self.of_recalcul_pa)
