# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class OFProductBrandHook(models.AbstractModel):
    _name = 'of.product.brand.hook'

    @api.model
    def _post_update_hook_v10_0_1_1_0(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_product_brand')])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < "10.0.1.1.0"
        if actions_todo:
            rule1 = self.env.ref('of_product_brand.brand_product_rule_internal_user', raise_if_not_found=False)
            rule2 = self.env.ref('of_product_brand.product_product_rule_internal_user', raise_if_not_found=False)
            rule3 = self.env.ref('of_product_brand.product_template_rule_internal_user', raise_if_not_found=False)
            if rule1:
                rule1.write({'domain_force': "[('id', 'not in', user.of_readonly_brand_ids.ids)]"})
            if rule2:
                rule2.write({'domain_force': "[('brand_id', 'not in', user.of_readonly_brand_ids.ids)]"})
            if rule3:
                rule3.write({'domain_force': "[('brand_id', 'not in', user.of_readonly_brand_ids.ids)]"})
