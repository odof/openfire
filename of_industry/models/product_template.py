# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_industry_id = fields.Many2one(
        comodel_name="of.industry", string="Industry", compute="_compute_of_industry_id", store=True, readonly=False
    )
    of_code = fields.Char(related="of_industry_id.code")

    @api.depends("categ_id", "categ_id.of_industry_id")
    def _compute_of_industry_id(self):
        for product in self:
            if product.categ_id.of_industry_id:
                product.of_industry_id = product.categ_id.of_industry_id.id
            else:
                product.of_industry_id = False
