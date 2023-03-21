# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    of_template_id = fields.Many2one(comodel_name='account.move.template', string="Original template")
