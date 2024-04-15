# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models, registry


class OFRemoveUnusedProducts(models.TransientModel):
    _name = "of.remove.unused.products"

    def action_button_remove_unused_products(self):
        cpt = 0
        brands = self.env["of.product.brand"].browse(self._context["active_ids"]).with_context(active_test=False)

        # Attention, le curseur temporaire ne doit pas s'appeler cr.
        # La fonction de traduction _() cherche l'existence d'une variable cr dans la fonction appelante.
        # Elle utiliserait donc un cursor déjà fermé, ce qui annulerait la traduction.
        with registry(self._cr.dbname).cursor() as new_cr:
            for product in self.env(cr=new_cr)["product.template"].browse(brands.mapped("product_ids")._ids):
                try:
                    product.unlink()
                    new_cr.commit()
                    cpt += 1
                except Exception:
                    new_cr.rollback()
        return self.env["of.popup.wizard"].popup_return(
            _("%i products were removed") % cpt, titre=_("Products removal")
        )
