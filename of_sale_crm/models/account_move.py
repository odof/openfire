# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    of_canvasser_id = fields.Many2one(
        comodel_name='res.users',
        string="Canvasser",
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user,
    )
