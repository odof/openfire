# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_preconfirm(self):
        res = super(SaleOrder, self).action_preconfirm()
        create_portal_users = self.env['ir.values'].get_default('base.config.settings', 'of_create_portal_users')
        if create_portal_users == 'order_preconfirm':
            self.mapped('partner_id')._create_portal_user()
        return res
