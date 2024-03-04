# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "of.import.product.config.template"]

    brand_id = fields.Many2one(inverse="_inverse_brand_id")

    def _inverse_brand_id(self):
        """Define a dummy inverse method, to get this fields available in `of.import`"""
        pass

    of_is_net_price = fields.Boolean(
        string="Based on net price",
        help="""If this box is checked, the item prices are calculated based on a purchase price
        provided by the supplier.
        Otherwise, they are based on the net list price excluding taxes.""",
    )

    def action_button_update_from_brand(self):
        """
        Recalcule les champs de l'article en fonction de la configuration de la marque
        et des paramètres d'import de l'article (dans product_supplierinfo)
        """
        # On prétend venir d'un import afin de lancer la propagation du coût sur les différentes sociétés
        self = self.with_context(from_import=True)
        for product in self:
            supplier = product.brand_id.partner_id
            for seller in product.seller_ids:
                if seller.partner_id == supplier:
                    values = product.brand_id.compute_product_values(
                        seller.of_public_price_untaxed,
                        seller.of_product_category_name,
                        product.uom_id,
                        product.uom_po_id,
                        product,
                        seller.price,
                        cost=product.get_cost(),
                        based_on_price=product.of_is_net_price,
                    )
                    if values := {
                        key: val
                        for key, val in values.items()
                        if self._fields[key].convert_to_write(product[key], product) != val
                    }:
                        product.write(values)
                    break
