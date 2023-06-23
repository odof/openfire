# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    # Brought back a old V10 field here. We must choose to keep it or not and use the standard delay field
    of_days = fields.Integer(string="Delay", help="Number of days before the activity is considered as due.")
    of_team_id = fields.Many2one(comodel_name='crm.team', string="Team")
    of_user_id = fields.Many2one(comodel_name='res.users', string="Assigned to")
    of_short_name = fields.Char(string="Short Name", required=True, translate=True)
    of_object = fields.Selection(selection=[('crm.lead', "Opportunity")], string="Object")
    of_compute_date_id = fields.Many2one(
        comodel_name='of.crm.compute.date',
        string="Compute Date",
        domain="[('res_model', '=', of_object)]",
    )
    of_compute_date_res_field = fields.Char(
        related='of_compute_date_id.res_field',
        string="Compute Date Field",
        readonly=True,
    )
    of_automatic_recompute = fields.Boolean(string="Automatic recompute", default=True)
    of_load_attachment = fields.Boolean(string="Load an attachment")

    @api.onchange('of_team_id')
    def _onchange_team_id(self):
        domain = {'of_user_id': False}
        if not self.of_team_id:
            self.of_user_id = False
        if self.of_team_id and self.of_team_id.member_ids:
            user_ids = self.of_team_id.member_ids.ids
            domain['of_user_id'] = f"[('id', 'in', {user_ids})]"
        return {'domain': domain}
