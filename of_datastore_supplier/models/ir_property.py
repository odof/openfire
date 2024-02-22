# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class Property(models.Model):
    _inherit = "ir.property"

    @api.model
    def _get_multi(self, name, model, ids):
        if (
            model == "product.product"
            and name == "standard_price"
            and (of_product_user_id := "of_product_user_id" in self.env.context)
        ):
            # Distributors can't read the standard price if they do not belong to the margin group
            group = self.env.ref("of_sale.of_group_sale_responsible", raise_if_not_found=False)
            profile = self.env.ref("of_datastore_supplier.user_profile_distributor")
            user = self.env["res.users"].browse(of_product_user_id)
            if user.of_user_profile_id == profile and group and not user.has_group("of_sale.of_group_sale_responsible"):
                return {id: 0.0 for id in ids}
        return super()._get_multi(name, model, ids)
