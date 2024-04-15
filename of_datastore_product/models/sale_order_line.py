# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "of.datastore.product.reference"]

    of_brand_id = fields.Many2one(
        comodel_name="of.product.brand",
        string="Brand filter",
        compute="_compute_of_brand_id",
        store=True,
        readonly=False,
        help="This field allows you to restrict the items offered to a single brand.\n"
        "Entering this field also allows searching in the product datastore.\n"
        "Use equivalent to the code m:XXX in the article search, where XXX is the brand code",
    )

    @api.depends("product_id")
    def _compute_of_brand_id(self):
        for line in self:
            if line.product_id and line.of_brand_id and line.product_id.brand_id != line.of_brand_id:
                line.of_brand_id = False
