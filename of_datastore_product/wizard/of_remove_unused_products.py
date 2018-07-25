# -*- coding: utf-8 -*-

from odoo import models, api, registry, _

class OfRemoveUnusedProducts(models.TransientModel):
    _name = "of.remove.unused.products"

    @api.multi
    def action_remove_unused_products(self):
        cpt = 0
        brands = self.env['of.product.brand'].browse(self._context['active_ids']).with_context(active_test=False)

        with registry(self._cr.dbname).cursor() as cr:
            for product in self.env(cr=cr)['product.template'].browse(brands.mapped('product_ids')._ids):
                try:
                    product.unlink()
                    cr.commit()
                    cpt += 1
                except:
                    cr.rollback()
        return self.env['of.popup.wizard'].popup_return(_('%i products were removed') % cpt, titre=_('Products removal'))
