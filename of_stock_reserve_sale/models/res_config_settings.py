# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    of_auto_reserve = fields.Boolean(string=u"(OF) Réservation vers opération")

    @api.multi
    def set_of_auto_reserve_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'of_auto_reserve', self.of_auto_reserve)
