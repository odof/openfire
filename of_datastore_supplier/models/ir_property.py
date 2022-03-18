# -*- coding: utf-8 -*-

from odoo import models, api


class Property(models.Model):
    _inherit = 'ir.property'

    @api.model
    def get_multi(self, name, model, ids):
        if model == 'product.product' and name == 'standard_price' and 'of_product_user_id' in self._context:
            group = self.env.ref('of_sale.of_group_sale_marge_manager', raise_if_not_found=False)
            profile = self.env.ref('of_datastore_supplier.user_profile_distributor')
            user = self.env['res.users'].browse(self._context['of_product_user_id'])
            if user.of_user_profile_id == profile and group and not user.has_group(
                    'of_sale.of_group_sale_marge_manager'):
                return {id: 0.0 for id in ids}
        return super(Property, self).get_multi(name, model, ids)
