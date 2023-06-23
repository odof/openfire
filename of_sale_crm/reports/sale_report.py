# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_canvasser_id = fields.Many2one(comodel_name='res.users', string="Canvasser", readonly=True)

    def _select(self):
        res = super()._select()
        res += ", s.of_canvasser_id as of_canvasser_id"
        return res

    def _group_by(self):
        res = super()._group_by()
        res += ", s.of_canvasser_id"
        return res
