# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, api, fields, models


class OFMoveInterventionsToNextWeekWizard(models.TransientModel):
    _name = 'of.move.intervention.to.next.week.wizard'
    _description = "Wizard to move interventions to next week"

    @api.model
    def default_get(self, fields):
        res = super(OFMoveInterventionsToNextWeekWizard, self).default_get(fields)
        intervention_ids = self.env.context.get('active_ids', [])
        res['intervention_ids'] = [Command.set(intervention_ids)]
        res['intervention_count'] = len(intervention_ids)
        return res

    intervention_ids = fields.Many2many(
        comodel_name='calendar.event',
        relation='of_move_intervention_to_next_week_wizard_rel',
        column1='wizard_id',
        column2='intervention_id',
        string="Interventions",
    )
    intervention_count = fields.Integer(string="Intervention count", readonly=True)

    def action_button_validate(self):
        for intervention in self.with_context(force_move_next_week=True).intervention_ids:
            intervention.write(
                {
                    'start': intervention.start + timedelta(days=7),
                    'stop': intervention.stop + timedelta(days=7),
                }
            )
        return self.env.ref('of_planning.action_calendar_event').read()[0]
