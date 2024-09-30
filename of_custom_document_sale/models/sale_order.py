# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "of.custom.document.mixin"]

    @api.model
    def _allowed_reports(self):
        return ["sale.report_saleorder"]
