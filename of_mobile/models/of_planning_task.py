# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OFPlanningTask(models.Model):
    _inherit = 'of.planning.task'

    mobile = fields.Boolean(string="Mobile Task")

    def write(self, vals):
        res = super().write(vals)
        self.env['calendar.event'].action_update_date([('of_task_id', 'in', self.ids)])
        return res

    def unlink(self):
        self.env['calendar.event'].action_update_date([('of_task_id', 'in', self.ids)])
        return super().unlink()

    def action_button_toggle_mobile(self):
        self.ensure_one()
        intervention_template_obj = self.env['of.planning.intervention.template']
        if self.mobile and intervention_template_obj.search([('task_id', '=', self.id), ('mobile', '=', True)]):
            raise UserError(
                _("You cannot unpublish this task, as the associated intervention templates are published.")
            )

        self.mobile = not self.mobile

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = super()._prepare_graphql_domain(select, domain)

        if select:
            if 'mobile' in select:
                odoo_domain += [('mobile', '=', select.mobile)]

        return odoo_domain
