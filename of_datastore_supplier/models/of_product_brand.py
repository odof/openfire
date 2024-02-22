# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFProductBrand(models.Model):
    _inherit = "of.product.brand"

    update_note = fields.Text(
        help="This field is intended for distributors and allows to transmit information about the status "
        "of pricing."
    )

    datastore_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Shared Location",
        domain="[('usage', '=', 'internal')]",
        help="Location where the stock is shared",
    )
    datastore_stock_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Restrict by customer",
        context={"of_distributor_test": False, "search_default_of_distributor": True},
    )

    @api.model
    def of_access_stocks(self, brand_id):
        """
        Check if the current user has access to the stocks of a given brand.

        Args:
            brand_id (int): The ID of the brand to check access for.

        Returns:
            bool: True if the current user has access to the brand's stocks, False otherwise.
        """
        current_user_id = self.env.user.id
        brand = self.search([("id", "=", brand_id)])
        if not brand or not brand.datastore_location_id:
            return False
        return not brand.datastore_stock_user_ids or current_user_id in brand.datastore_stock_user_ids._ids
