# -*- coding: utf-8 -*-

from odoo import models, api, registry, _

class OfRemoveUnusedProducts(models.TransientModel):
    _name = "of.remove.unused.products"

    @api.multi
    def action_remove_unused_products(self):
        cpt = 0
        brands = self.env['of.product.brand'].browse(self._context['active_ids']).with_context(active_test=False)

        # Attention, le curseur temporaire ne doit pas s'appeler cr.
        # La fonction de traduction _() cherche l'existence d'une variable cr dans la fonction appelante.
        # Elle utiliserait donc un cursor déjà fermé, ce qui annulerait la traduction.
        with registry(self._cr.dbname).cursor() as cr_temp:
            for product in self.env(cr=cr_temp)['product.template'].browse(brands.mapped('product_ids')._ids):
                try:
                    product.unlink()
                    cr_temp.commit()
                    cpt += 1
                except Exception:
                    cr_temp.rollback()
        return self.env['of.popup.wizard'].popup_return(_('%i products were removed') % cpt, titre=_('Products removal'))
