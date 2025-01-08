# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_industry_id = fields.Many2one(
        comodel_name="of.industry", string="Industry", compute="_compute_of_industry_id", store=True, readonly=False
    )
    of_code = fields.Char(related="of_industry_id.code")

    of_has_standard_attributes = fields.Boolean(
        string="Has standard attributes",
        compute="_compute_of_has_standard_attributes",
    )

    of_has_technical_attributes = fields.Boolean(
        string="Has technical attributes",
        compute="_compute_of_has_technical_attributes",
    )

    @api.depends("categ_id", "categ_id.of_industry_id")
    def _compute_of_industry_id(self):
        for product in self:
            if product.categ_id.of_industry_id:
                product.of_industry_id = product.categ_id.of_industry_id.id
            else:
                product.of_industry_id = False

    @api.depends("of_code")
    def _compute_of_has_standard_attributes(self):
        for record in self:
            record.of_has_standard_attributes = False

    @api.depends("of_code")
    def _compute_of_has_technical_attributes(self):
        for record in self:
            record.of_has_technical_attributes = False
