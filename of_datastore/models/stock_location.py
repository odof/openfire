# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockLocation(models.Model):
    _name = "stock.location"
    _inherit = ["stock.location", "of.datastore.model"]
