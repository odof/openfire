# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    of_comment_template_ids = fields.Many2many(comodel_name="base.comment.template", string="Comment Template")
