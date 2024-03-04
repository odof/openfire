# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OfImportUpdateProductBrandProducts(models.TransientModel):
    _name = 'of.import.update.product.brand.products'

    brand_id = fields.Many2one(comodel_name='of.product.brand', string="Brand", required=True)
    product_ids = fields.Many2many(
        comodel_name='product.template', string="Products", domain="[('brand_id', '=', brand_id)]"
    )

    def action_button_update_products(self):
        self.ensure_one()
        products = self.product_ids or self.brand_id.product_ids
        products.action_button_update_from_brand()

        # Le délai renseigné dans la marque, si différent de 0, se propage dans les lignes fournisseurs
        # présentes dans l’onglet Inventaire des articles
        if self.brand_id.supplier_delay:
            products.mapped('seller_ids').filtered(lambda s: s.name == self.brand_id.partner_id).write(
                {
                    'delay': self.brand_id.supplier_delay,
                }
            )

        return True
