# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = [_name, "base_multi_image.owner"]

    of_product_image_domain_ids = fields.One2many(
        comodel_name="base_multi_image.image",
        string="Product images domain",
        compute="_compute_of_product_image_domain_ids",
    )
    of_product_image_ids = fields.Many2many(
        comodel_name="base_multi_image.image",
        string="Product images",
        compute="_compute_of_product_image_ids",
        readonly=False,
        store=True,
        domain="[('id', 'in', of_product_image_domain_ids)]",
    )

    @api.depends("product_id")
    def _compute_of_product_image_domain_ids(self):
        for line in self:
            images = line.product_id.product_tmpl_id.image_ids
            line.of_product_image_domain_ids = self.env["base_multi_image.image"].search([("id", "in", images.ids)])

    @api.depends("product_id")
    def _compute_of_product_image_ids(self):
        for line in self:
            images = line.product_id.product_tmpl_id.image_ids
            line.of_product_image_ids = [Command.set(images.ids)]
