# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, _
from odoo.exceptions import UserError


class OFResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def action_open_wizard_plan_intervention(self):
        self.ensure_one()
        if not self.geo_lat and not self.geo_lng:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))

        ir_values_obj = self.env['ir.values']
        planning_task_obj = self.env['of.planning.tache']
        tour_meetup_obj = self.env['of.tournee.rdv']
        context = self._context.copy()

        enable_quick_scheduling = ir_values_obj.get_default('of.intervention.settings', 'enable_quick_scheduling')
        default_planning_task_id = ir_values_obj.get_default('of.intervention.settings', 'default_planning_task_id')
        # In case of default task not being set, we start the wizard without pre-searching
        if not default_planning_task_id or not enable_quick_scheduling:
            form_view_id = self.env.ref('of_planning_tournee.view_rdv_intervention_complete_form_wizard').id
            return {
                'name': _("Plan intervention"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.tournee.rdv',
                'res_id': False,
                'views': [(form_view_id, 'form')],
                'target': 'new',
                'context': context
            }

        default_values = tour_meetup_obj.with_context(
            active_model=self._name,
            active_ids=self.ids,
        ).default_get(tour_meetup_obj._fields.keys())
        default_planning_task = \
            planning_task_obj.browse(default_planning_task_id) if default_planning_task_id else False
        default_values['duree'] = default_planning_task and default_planning_task.duree or 1.0
        time_slots_new = tour_meetup_obj.new(default_values)
        # onchange to compute fields on the time slots
        time_slots_new._onchange_partner_address_id()
        time_slots_new._onchange_service()
        time_slots_new._onchange_tache_id()
        time_slots_new._onchange_date_recherche_fin()
        wizard_values = tour_meetup_obj._convert_to_write(time_slots_new._cache)
        time_slots_wizard = tour_meetup_obj.create(wizard_values)
        # start time slots computing
        time_slots_wizard.compute()
        form_view_id = time_slots_wizard._get_wizard_form_view_id()
        return {
            'name': _("Plan intervention"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.tournee.rdv',
            'views': [(form_view_id, 'form')],
            'res_id': time_slots_wizard.id,
            'target': 'new',
            'context': context
        }
