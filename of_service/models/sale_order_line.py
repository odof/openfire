# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_request_line_id = fields.Many2one(comodel_name="of.service.request.line", string="Service Request Line")
