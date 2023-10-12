# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleConfigSettings(models.TransientModel):
    _inherit = "sale.config.settings"

    of_active_option = fields.Boolean(string="Activer l'option de création automatique de demande d'intervention")

    @api.multi
    def set_of_active_option(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_active_option', self.of_active_option)
