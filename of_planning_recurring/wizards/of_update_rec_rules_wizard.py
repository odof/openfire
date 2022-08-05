# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class OFUpdateRecRulesWizard(models.TransientModel):
    _name = 'of.update.rec.rules.wizard'
    _inherit = 'of.planning.recurring.mixin'

    @api.model
    def _domain_employee_ids(self):
        return self.env['of.planning.intervention']._domain_employee_ids()

    interv_origin_id = fields.Many2one(
        string=u"RDV d'origine", comodel_name='of.planning.intervention', readonly=True)
    occurence_id_str = fields.Char(string=u"ID de l'occurence", readonly=True, help=u"ID virtuel")
    recurrency_origin = fields.Boolean(
        string=u"Récurrence du RDV d'origine", related='interv_origin_id.recurrency', readonly=True)
    employee_ids = fields.Many2many(
        comodel_name='hr.employee', relation='of_employee_intervention_rec_rules_rel', column1='intervention_id',
        column2='employee_id', string=u"Intervenants", required=True, domain=lambda self: self._domain_employee_ids())
    date_occurence = fields.Date(string=u"Date de l'occurence", readonly=True)
    jour_ids = fields.Many2many(string=u"Jours", comodel_name='of.jours', compute='_compute_jour_ids')
    rec_start_date = fields.Date(
        string=u"À partir du", help=u"Les règles de récurrence sont appliquées à partir de cette date", required=True)
    rec_stop_date = fields.Date(
        string=u"Jusqu'au", help=u"Les règles de récurrence sont appliquées jusqu'à cette date",
        compute='_compute_rec_stop_date')

    start_hour = fields.Float(string=u"Heure de début", required=True)
    end_hour = fields.Float(string=u"Heure de fin", required=True)
    duration_computed = fields.Float(string=u"Durée calculée", compute='_compute_duration_computed')
    duration = fields.Float(string=u"Durée sauvegardée")

    is_rule_modified = fields.Boolean(
        string=u"Règles modifiées", compute='_compute_is_rule_modified',
        help=u"Si les règles de récurrence ont été modifiées, on ne peut pas 'modifier cette occurence uniquement'")
    is_start_modified = fields.Boolean(
        string=u"Date de début modifiée", compute='_compute_is_start_modified',
        help=u"Si la date de début a été modifiée, on doit 'modifier toutes les occurences'")
    alert_coherence_hours = fields.Boolean(
        string=u"Incohérence dans les heures", compute="_compute_alert_coherence_hours")

    @api.constrains('start_hour', 'end_hour')
    def check_coherence_hours(self):
        for interv in self:
            if interv.alert_coherence_hours:
                raise UserError(_(u"Attention /!\\ l'heure de fin doit être supérieure à l'heure de début"))

    @api.depends(
        'byday', 'recurrency', 'final_date', 'rrule_type', 'month_by', 'interval', 'count', 'end_type', 'mo', 'tu',
        'we', 'th', 'fr', 'sa', 'su', 'day', 'week_list')
    def _compute_rec_stop_date(self):
        for wizard in self:
            end_dt = wizard._get_recurrency_end_date(format_dt=True)
            wizard.rec_stop_date = fields.Date.to_string(end_dt)

    @api.depends('mo', 'tu', 'we', 'th', 'fr', 'sa', 'su')
    def _compute_jour_ids(self):
        jour_obj = self.env['of.jours']
        for wizard in self:
            jour_num_list = wizard.get_jour_num()
            jours = jour_obj.search([('numero', 'in', jour_num_list)])
            wizard.jour_ids = jours.ids

    @api.depends('start_hour', 'end_hour')
    def _compute_duration_computed(self):
        for wizard in self:
            if wizard.start_hour and wizard.end_hour:
                wizard.duration_computed = wizard.end_hour - wizard.start_hour

    @api.depends(
        'byday', 'recurrency', 'final_date', 'rrule_type', 'month_by', 'interval', 'count', 'end_type', 'mo', 'tu',
        'we', 'th', 'fr', 'sa', 'su', 'day', 'week_list', 'interv_origin_id')
    def _compute_is_rule_modified(self):
        for wizard in self:
            origin = wizard.interv_origin_id
            if origin.recurrency != wizard.recurrency \
                    or origin.interval != wizard.interval \
                    or origin.rrule_type != wizard.rrule_type \
                    or origin.end_type != wizard.end_type \
                    or origin.count != wizard.count \
                    or origin.final_date != wizard.final_date:
                wizard.is_rule_modified = True
            elif wizard.rrule_type == 'weekly' \
                    and any([origin[field] != wizard[field] for field in ('mo', 'tu', 'we', 'th', 'fr', 'sa', 'su')]):
                wizard.is_rule_modified = True
            elif wizard.rrule_type == 'monthly' \
                    and origin['month_by'] != wizard['month_by'] \
                    or wizard['month_by'] == 'date' and origin['day'] != wizard['day'] \
                    or wizard['month_by'] == 'day' and \
                    (origin['byday'] != wizard['byday'] or origin['week_list'] != wizard['week_list']):
                wizard.is_rule_modified = True
            else:
                wizard.is_rule_modified = False

    @api.depends('rec_start_date', 'interv_origin_id')
    def _compute_is_start_modified(self):
        for wizard in self:
            origin = wizard.interv_origin_id
            if origin.date_date != wizard.rec_start_date:
                wizard.is_start_modified = True
            else:
                wizard.is_start_modified = False

    @api.depends('start_hour', 'end_hour')
    def _compute_alert_coherence_hours(self):
        for wizard in self:
            wizard.alert_coherence_hours = not (0 <= wizard.start_hour < wizard.end_hour < 24)

    @api.onchange('jour_ids')
    def _onchange_jour_ids(self):
        self.ensure_one()
        day_field_vals = self.jour_ids.get_rec_fields()
        self.update(day_field_vals)
        self._compute_rec_stop_date()

    @api.onchange('start_hour')
    def _onchange_start_hour(self):
        self.ensure_one()
        if 0 <= self.start_hour < 24:
            self.end_hour = self.start_hour + self.duration

    @api.onchange('end_hour')
    def _onchange_end_hour(self):
        self.ensure_one()
        if 0 <= self.end_hour < 24:
            self.duration = self.duration_computed

    @api.onchange('count')
    def _onchange_count(self):
        if self.count > 100:
            self.count = 100

    @api.onchange('end_type', 'final_date')
    def _onchange_final_date(self):
        if self.end_type == 'end_date' and self.final_date:
            date_max = fields.Date.from_string(self.rec_start_date) + relativedelta(years=1)
            final_date = fields.Date.from_string(self.final_date)
            if final_date > date_max:
                self.final_date = fields.Date.to_string(date_max)

    def button_edit_all(self):
        # ici le RDV est déjà récurrent et reste récurrent
        write_vals = self.get_write_vals(all=True)
        self.interv_origin_id.write(write_vals)
        if self.is_rule_modified:
            detached = self.env['of.planning.intervention'].with_context(virtual_id=False)\
                .search([('recurrent_id', '=', self.interv_origin_id.id)])
            detached.write({'recurrent_id': False, 'recurrent_date': False})
        return True

    def button_edit_this_and_next(self):
        # ici on termine la récurrence de ce RDV après l'avoir copié, puis on modifie la récurrence de la copie
        write_vals = self.get_write_vals()
        new_event = self.interv_origin_id.detach_recurring_event(only_one=False, occurence_id=self.occurence_id_str)
        new_event.write(write_vals)
        if self.is_rule_modified:
            detached = self.env['of.planning.intervention'].with_context(virtual_id=False)\
                .search([('recurrent_id', '=', self.interv_origin_id.id)])
            detached.write({'recurrent_id': False, 'recurrent_date': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.planning.intervention',
            'view_mode': 'form',
            'res_id': new_event.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }

    def button_edit_this(self):
        # ici on n'arrête pas la récurrence ni ne modifie les règles, mais cette occurence doit être ignorée
        # on copie le RDV sans sa récurrence et on modifie les heures et intervenants
        write_vals = self.get_write_vals(with_rec=False)
        new_event = self.interv_origin_id.detach_recurring_event(only_one=True, occurence_id=self.occurence_id_str)
        new_event.write(write_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.planning.intervention',
            'view_mode': 'form',
            'res_id': new_event.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }

    @api.multi
    def button_edit_this_disabled(self):
        # pour ne pas masquer le bouton "Uniquement cette occurence" mais le désactiver
        # avec une info-bulle explicative
        return {"type": "ir.actions.do_nothing"}

    def button_make_rec(self):
        # ici on passe d'un RDV non récurrent à un RDV récurrent.
        write_vals = self.get_write_vals()
        self.interv_origin_id.write(write_vals)
        return True

    def button_undo_rec(self):
        # et enfin, ici on annule la récurrence du RDV
        write_vals = self.get_write_vals(with_rec=False)
        self.interv_origin_id.write(write_vals)
        return True

    def get_jour_num(self):
        field_names = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        res = []
        for i in range(7):
            if self[field_names[i]]:
                res.append(i+1)
        return res

    @api.multi
    def get_datetimes(self, all=False):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        # en cas de modification de toutes les occurences, la date à prendre en compte est celle de début de récurrence
        date_da = all and fields.Date.from_string(self.rec_start_date) or fields.Date.from_string(self.date_occurence)
        date_debut_dt = datetime.combine(date_da, datetime.min.time()) + timedelta(hours=self.start_hour)
        date_debut_dt = tz.localize(date_debut_dt, is_dst=None).astimezone(pytz.utc)
        date_fin_dt = datetime.combine(date_da, datetime.min.time()) + timedelta(hours=self.end_hour)
        date_fin_dt = tz.localize(date_fin_dt, is_dst=None).astimezone(pytz.utc)
        return fields.Datetime.to_string(date_debut_dt), fields.Datetime.to_string(date_fin_dt)

    @api.multi
    def get_write_vals(self, with_rec=True, all=False):
        write_vals = {}
        if with_rec:
            for field_name in self._get_recurrent_fields():
                write_vals[field_name] = self[field_name]
            write_vals['rrule'] = self.rrule
            type_misc = self.env.ref('of_planning_recurring.of_service_type_misc', raise_if_not_found=False)
            write_vals['type_id'] = type_misc and type_misc.id
        else:
            write_vals['recurrency'] = False
        date, date_deadline = self.get_datetimes(all=all)
        write_vals['all_day'] = self.all_day
        write_vals['date'] = date
        write_vals['date_deadline_forcee'] = date_deadline
        write_vals['duree'] = self.duration_computed
        write_vals['employee_ids'] = [(6, 0, self.employee_ids.ids)]
        return write_vals
