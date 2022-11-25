# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    of_parc_installe_auto = fields.Boolean(
        string=u"(OF) Création automatique du parc installé",
        help=u"Créer automatiquement le parc installé lors de la confirmation du BL si un numéro de série "
        u"est renseigné.")

    @api.multi
    def set_of_parc_installe_auto_defaults(self):
        if not bool(self.group_stock_production_lot):
            return self.env['ir.values'].sudo().set_default('stock.config.settings', 'of_parc_installe_auto', False)
        else:
            return self.env['ir.values'].sudo().set_default(
                'stock.config.settings', 'of_parc_installe_auto', self.of_parc_installe_auto)
