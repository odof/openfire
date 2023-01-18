# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def unlink(self):
        # Le ondelete cascade dans product.product fait qu'on ne passe pas dans le unlink de product.product
        # doit donc être fait également dans ce unlink()
        ir_values_obj_sudo = self.env['ir.values'].sudo()
        product_prorata_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_prorata_id_setting')
        product_situation_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_situation_id_setting')
        product_retenue_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_retenue_id_setting')
        ids_deleted = self.with_context(active_test=False).mapped('product_variant_ids')._ids
        res = super(ProductTemplate, self).unlink()
        if product_prorata_id in ids_deleted:
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_prorata_id_setting', False)
        if product_situation_id in ids_deleted:
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_situation_id_setting', False)
        if product_retenue_id in ids_deleted:
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_retenue_id_setting', False)
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _auto_init(self):
        ir_values_obj_sudo = self.env['ir.values'].sudo()
        product_obj = self.env['product.product']
        res = super(ProductProduct, self)._auto_init()
        # Setting the value to False because it isn't used when this module is installed
        product_prorata_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_prorata_id_setting')
        product_situation_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_situation_id_setting')
        product_retenue_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_retenue_id_setting')
        # search et non pas browse, browse va être vrai mais fera un raise si on tente d'accéder à un champ
        if not product_obj.search([('id','=', product_prorata_id)]):
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_prorata_id_setting', False)
        if not product_obj.search([('id','=', product_situation_id)]):
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_situation_id_setting', False)
        if not product_obj.search([('id','=', product_retenue_id)]):
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_retenue_id_setting', False)
        return res

    @api.multi
    def unlink(self):
        ir_values_obj_sudo = self.env['ir.values'].sudo()
        product_prorata_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_prorata_id_setting')
        product_situation_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_situation_id_setting')
        product_retenue_id = ir_values_obj_sudo.get_default('sale.config.settings', 'of_product_retenue_id_setting')
        ids_deleted = self._ids
        res = super(ProductProduct, self).unlink()
        if product_prorata_id in ids_deleted:
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_prorata_id_setting', False)
        if product_situation_id in ids_deleted:
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_situation_id_setting', False)
        if product_retenue_id in ids_deleted:
            ir_values_obj_sudo.set_default('sale.config.settings', 'of_product_retenue_id_setting', False)
        return res
