# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockInventoryLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "of.datastore.product.reference"]
