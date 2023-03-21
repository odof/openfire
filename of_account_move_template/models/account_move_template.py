# License: AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveTemplate(models.Model):
    _inherit = 'account.move.template'

    line_ids = fields.One2many(copy=True)
    of_move_ids = fields.One2many(
        comodel_name='account.move', inverse_name='of_template_id', string="Accounting vouchers")
    of_moves_count = fields.Integer(compute='_compute_of_moves_count', string="Nb. vouchers", store=True)
    of_moves_last_date = fields.Date(compute='_compute_of_moves_last_date', string="Last voucher", store=True)
    of_recurring = fields.Boolean(string="Recurring")
    of_rec_interval = fields.Integer(string="Repeat every", default=1, required=True)
    of_rec_interval_type = fields.Selection(
        selection=[('days', "Days"), ('months', "Months"), ('years', "Years")],
        string="Time unit", default='months', required=True)
    of_rec_number = fields.Integer(string="Number of vouchers", default=12, required=True)
    of_prorata = fields.Boolean(
        string="Prorata",
        help="The amount of the entries will be adjusted pro rata to the month for the first and last month.",
    )
    of_reversal = fields.Selection(selection=[
        ('none', "No reversal"), ('first', "Start date"), ('last', "End date"), ('custom', "Chosen date")],
        string="Reverse the entry", default='none', required=True)
    of_reversal_date = fields.Date(
        string="Reversal date",
        help="The year will be automatically recalculated in the accounting documents creation tool.")

    @api.depends('of_move_ids')
    def _compute_of_moves_count(self):
        for template in self:
            template.of_moves_count = len(template.of_move_ids)

    @api.depends('of_move_ids.date')
    def _compute_of_moves_last_date(self):
        for template in self:
            template.of_moves_last_date = template.of_move_ids[:1].date if template.of_move_ids else False

    def of_action_view_moves(self):
        action = self.env.ref('account.action_move_line_form').read()[0]
        action['domain'] = [('of_template_id', 'in', self.ids)]
        action['context'] = {
            'default_of_template_id': len(self) == 1 and self.id,
        }
        return action
