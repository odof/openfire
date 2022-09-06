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
        context = self._context.copy()
        context['default_slots_display_mode'] = ir_values_obj.get_default(
            'of.intervention.settings', 'slots_display_mode')
        context['default_search_type'] = ir_values_obj.get_default(
            'of.intervention.settings', 'search_type') or 'distance'
        form_view_id = self.env.ref('of_planning_tournee.view_rdv_intervention_complete_form_wizard').id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.tournee.rdv',
            'res_id': False,
            'views': [(form_view_id, 'form')],
            'target': 'new',
            'context': context
        }
