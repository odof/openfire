# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    of_datastore_line_id = fields.Integer(string="Order line ID customer base", copy=False)

    def connector_force_compute_values(self):
        """Allows private methods to be called via xmlrpc to force the calculation of some fields"""
        self._compute_tax_id()
        self._compute_discount()
        return True
