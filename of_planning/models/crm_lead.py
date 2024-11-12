# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class CrmLead(models.Model):
    _inherit = "crm.lead"

    of_intervention_ids = fields.One2many(
        comodel_name="calendar.event", inverse_name="of_lead_id", string="Interventions"
    )
    of_intervention_count = fields.Integer(string="# Interventions", compute="_compute_of_intervention_count")

    @api.depends("of_intervention_ids")
    def _compute_of_intervention_count(self):
        for lead in self:
            lead.of_intervention_count = len(lead.of_intervention_ids)

    def action_button_view_intervention(self):
        action = self.env.ref("of_planning.action_calendar_event").sudo().read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action["context"])
            context.update(
                {
                    "default_of_partner_id": self.partner_id.id or False,
                    "default_of_address_id": self.partner_id.id or False,
                    "default_of_lead_id": self.id,
                }
            )
            if not self.of_intervention_ids or len(self.of_intervention_ids) > 1:
                domain = safe_eval(action["domain"]) if action.get("domain") else []
                domain += [("of_lead_id", "=", self.id)]
                action["domain"] = domain
            elif len(self.of_intervention_ids) == 1:
                form_view = self.env.ref("of_planning.calendar_event_view_form", raise_if_not_found=False)
                # Put the form view in first position
                action["views"] = [(form_view and form_view.id or False, "form")] + [
                    (state, view) for state, view in action.get("views", []) if view != "form"
                ]
                action["res_id"] = self.of_intervention_ids.id
            action["context"] = context
        action = self.mapped("of_intervention_ids")._get_calendar_event_action_views(action)
        return action
