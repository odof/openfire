# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFSaleDiscountHook(models.AbstractModel):
    _name = 'of.sale.discount.hook'

    @api.model
    def _pre_update_hook_v10_0_1_1_0(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_sale_discount'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version and module_self.latest_version < '10.0.1.1.0':
            # init M2M picking_manual_ids relation based on picking_id field
            view = self.env.ref(
                'of_sale_discount.of_sale_discount_view_account_config_settings', raise_if_not_found=False)
            if view:
                view.unlink()
