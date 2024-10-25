# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPoujoulatCartItemWizard(models.TransientModel):
    _name = "of.poujoulat.cart.item.wizard"
    _description = "Wizard line to send PO cart line to Poujoulat"

    wizard_id = fields.Many2one(comodel_name="of.poujoulat.cart.wizard", required=True, ondelete="cascade")
    product_id = fields.Many2one(comodel_name="product.product", string="Product", required=True)
    quantity = fields.Float()
    artas400 = fields.Char(related="product_id.of_poujoulat_artas400", readonly=True)
    variant = fields.Integer(related="product_id.of_poujoulat_variant", readonly=True)
    conditioning_unit = fields.Char(related="product_id.of_poujoulat_cond_unit", readonly=True)

    def _get_estimate_values(self):
        """
        Generate a dictionary of product values required for estimating, based on the selected
        product's Poujoulat-specific fields.

        Returns:
            dict: A dictionary containing 'artas400', 'qty', 'variant', and 'unitCond' if
                all required values are present; otherwise, an empty dictionary.
        """
        self.ensure_one()
        if (
            not self.product_id.of_poujoulat_artas400
            or not self.product_id.of_poujoulat_variant
            or not self.product_id.of_poujoulat_cond_unit
        ):
            return {}
        return {
            "artas400": self.product_id.of_poujoulat_artas400,
            "qty": self.quantity,
            "variant": self.product_id.of_poujoulat_variant,
            "unitCond": self.product_id.of_poujoulat_cond_unit,
        }
