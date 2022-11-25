# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_transfer(self):
        u"""
        Créé automatiquement un parc installé pour le client si param de config et type BL
        """
        res = super(StockPicking, self).do_transfer()
        if len(self) == 1 and res and self.user_has_groups('stock.group_production_lot') and \
                self.picking_type_id.code == 'outgoing' and\
                self.env['ir.values'].get_default('stock.config.settings', 'of_parc_installe_auto'):
            lots = self.pack_operation_product_ids.mapped('pack_lot_ids').mapped('lot_id')
            if lots:
                lots.sudo().creer_parc_installe(self)
        return res
