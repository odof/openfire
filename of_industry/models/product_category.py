# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    of_industry_id = fields.Many2one(comodel_name="of.industry", string="Industry")
