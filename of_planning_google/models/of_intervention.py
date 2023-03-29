# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    google_create = fields.Boolean(string="Created from Google Calendar")
    google_synchro_date = fields.Datetime(
        string="Google synchro date",
        help="This fields is updated whenever there is a synchronisation made between google and odoo")
    google_internal_event_id = fields.Char(string="Google Calendar Event Id")
    google_upload_fail = fields.Boolean(string="Upload to google failed")
    partner_ids = fields.Many2many(
        string="Other participants", comodel_name='res.partner', relation='of_intervention_partner_rel',
        column1='intervention_id', column2='partner_id')
    google_address = fields.Char(string="Google address")

    @api.model
    def get_fields_need_update_google(self):
        u"""Used when creating/updating from Google calendar"""
        recurrent_fields = self._get_recurrent_fields()
        return recurrent_fields + ['name', 'description', 'all_day', 'date', 'duree', 'date_deadline_forcee',
                                   'forcer_dates', 'state', 'employee_ids', 'partner_ids', 'active']

    @api.multi
    def write(self, values):
        sync_fields = set(self.get_fields_need_update_google())
        if (set(values.keys()) & sync_fields) and 'google_synchro_date' not in values.keys() \
                and 'NewMeeting' not in self._context and 'no_google_synchro_update' not in self._context:
            if 'google_synchro_date' in self._context:
                values['google_synchro_date'] = self._context.get('google_synchro_date')
            else:
                values['google_synchro_date'] = fields.Datetime.now()
        return super(OFPlanningIntervention, self).write(values)

    @api.multi
    def copy(self, default=None):
        default = default or {}
        if default.get('write_type', False):
            del default['write_type']
        elif not default.get('google_synchro_date'):
            if default.get('recurrent_id', False):
                default['google_synchro_date'] = fields.Datetime.now()
            else:
                default['google_synchro_date'] = False
        return super(OFPlanningIntervention, self).copy(default)

    @api.multi
    def unlink(self, can_be_deleted=False):
        return super(OFPlanningIntervention, self).unlink(can_be_deleted=can_be_deleted)

    def get_name_for_update(self):
        self.ensure_one()
        tache_google = self.env.ref('of_planning_google.tache_google', raise_if_not_found=False)
        # do not update name for intervs created from google calendar
        if self.name and self.tache_id and tache_google and self.tache_id.id == tache_google.id:
            return self.name
        return super(OFPlanningIntervention, self).get_name_for_update()

    @api.multi
    def action_edit_recurrency(self):
        res = super(OFPlanningIntervention, self).action_edit_recurrency()
        if res.get('res_id'):
            wizard = self.env['of.update.rec.rules.wizard'].browse(res.get('res_id'))
            wizard.partner_ids = self.partner_ids
        return res
