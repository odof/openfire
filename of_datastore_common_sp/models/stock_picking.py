# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_datastore_anomaly = fields.Boolean(string="In Anomaly")
    of_datastore_id = fields.Integer(string="Transfer voucher ID connected base")
