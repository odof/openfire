# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.exceptions import UserError


class OFService(models.Model):
    _inherit = 'of.service'

    @api.multi
    def action_open_wizard_plan_intervention(self):
        self.ensure_one()
        if self.address_id and not self.address_id.geo_lat and not self.address_id.geo_lng:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))

        tour_meetup_obj = self.env['of.tournee.rdv']
        context = self._context.copy()
        default_values = tour_meetup_obj.with_context(
            active_model=self._name,
            active_ids=self.ids,
        ).default_get(tour_meetup_obj._fields.keys())
        default_values['duree'] = self.duree or self.tache_id.duree or 1.0
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
