# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    of_intervention_line_id = fields.Many2one(comodel_name='of.planning.intervention.line', string="Planned line")
