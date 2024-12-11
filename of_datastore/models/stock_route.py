# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockRoute(models.Model):
    _name = "stock.route"
    _inherit = ["stock.route", "of.datastore.model"]
