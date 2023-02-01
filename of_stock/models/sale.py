# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        # si la réservation est faite automatiquement lors de la validation de la commande
        # alors on change la contremarque
        res = super(SaleOrder, self.with_context(contremarque=True)).action_confirm()
        return res
