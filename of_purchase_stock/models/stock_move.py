# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _


class StockMove(models.Model):
    _inherit = "stock.move"

    replenished = fields.Boolean(string="Approvisionné")
