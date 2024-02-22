# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

import odoo.addons.base.models.decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_stock_informations = fields.Text(string="Stock Informations")
    of_next_price_list = fields.Float(string="Next Pricelist", digits=dp.get_precision("Product Price"), default=0.0)
    of_next_price_list_date = fields.Date(string="Next Pricelist Date")

    @api.depends("product_variant_ids", "product_variant_ids.standard_price")
    def _compute_standard_price(self):
        # Lock on purchase price reading.
        # Function not used by Product datastore call
        # This protection is preventive and protects in case of xmlrpc call or direct access to the central base
        group = self.env.ref("of_sale.of_group_sale_responsible", raise_if_not_found=False)
        user = self.env.user
        if user.of_is_distributor and group and not user.has_group("of_sale.of_group_sale_responsible"):
            for template in self:
                template.standard_price = 0.0
        else:
            super()._compute_standard_price()

    def of_datastore_get_quantities(self):
        self.ensure_one()
        product = self.with_context(location=self.brand_id.datastore_location_id.id)
        return product.qty_available - product.outgoing_qty, product.of_stock_informations or _("No information")
