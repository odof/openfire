# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_datastore_sale_misc_product_id = fields.Many2one(
        comodel_name="product.product",
        string="(OF) Miscellaneous items for the sales connector",
        help="Article used by the sales connector if no article corresponds to the reference received",
        config_parameter="of.datastore.sale.of_datastore_sale_misc_product_id",
    )
    group_of_group_datastore_brand_dropshipping = fields.Boolean(
        string="(OF) Dropshipping",
        help="Authorizes the use of dropshipping on brands",
        implied_group="of_datastore_sale.of_group_datastore_brand_dropshipping",
    )
