# -*- encoding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

from odoo.addons.of_utils.models.of_utils import float_2_heures_minutes, heures_minutes_2_float


class OFServiceCreateInterventionWizard(models.TransientModel):
    _name = 'of.service.create.intervention.wizard'
    _description = u"Assistant de création de RDV depuis les DI"

    employee_id = fields.Many2one(comodel_name='hr.employee', string=u"Intervenant")
    start_date = fields.Datetime(string=u"Date de début")
    line_ids = fields.One2many(
        comodel_name='of.service.create.intervention.line.wizard', inverse_name='wizard_id', string=u"Lignes")
    show_warning = fields.Boolean(string=u"Avertissement", compute='_compute_show_warning')

    @api.depends('employee_id', 'start_date', 'line_ids')
    def _compute_show_warning(self):
        for rec in self:
            if rec.employee_id and rec.start_date and rec.line_ids:
                # Check if wizard start date is inside employee work hours
                start_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(rec.start_date))
                start_hour = round(start_date.hour + start_date.minute / 60.0 + start_date.second / 3600.0, 5)
                worktime = rec.employee_id.get_horaires_date(rec.start_date)[rec.employee_id.id]
                for start, end in worktime:
                    if start <= start_hour < end:
                        break
                else:
                    rec.show_warning = True
                    continue
            rec.show_warning = False

    @api.multi
    def action_create_intervention(self):
        self.ensure_one()

        intervention_obj = self.env['of.planning.intervention']
        new_interventions = self.env['of.planning.intervention']
        group_flex = self.env.user.has_group('of_planning.of_group_planning_intervention_flexibility')
        tz = pytz.timezone('Europe/Paris')
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        current_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.start_date))
        services_to_process = self.line_ids.mapped('service_id')

        # We loop on services to process until they are all scheduled
        while services_to_process:
            current_day = current_date.date()
            # Employee work hours of the current day
            worktime = self.employee_id.get_horaires_date(current_day)[self.employee_id.id]
            if not worktime:
                current_date = current_date + relativedelta(days=1, hour=0, minute=0, second=0)
                continue
            # Employee existing interventions on the current day
            interventions = intervention_obj.with_context(virtual_id=True).search([
                ('employee_ids', 'in', self.employee_id.id),
                ('date', '<=', fields.Date.to_string(current_day)),
                ('date_deadline', '>=', fields.Date.to_string(current_day)),
                ('state', 'not in', ('cancel', 'postponed'))], order='date')
            # Employee unavailability timeline on the current day
            day_timeline = self.env['of.planning.tournee']._get_employee_day_unavailability_timeline(
                fields.Date.to_string(current_day), interventions, worktime)
            duration = services_to_process[0].duree

            # We try to find a free slot with enough duration to process the current service
            last_end = 0
            start_time = False
            current_hour = heures_minutes_2_float(current_date.hour, current_date.minute)
            segmentation = services_to_process[0].template_id.segmentation_allowed
            for start, end in day_timeline:
                if last_end >= current_hour and start - last_end >= duration:
                    # We found it, break
                    start_time = last_end
                    break
                # When segmentation is allowed on the service template,
                # we check if service can be scheduled on 2 days or around a day break
                if segmentation and last_end >= current_hour and start - last_end > 0:
                    # We check if we are in a free slot just before break or just before end of the day
                    time_segment = filter(lambda time: start == time[1], worktime)
                    if time_segment:
                        time_segment = time_segment[0]
                        remaining_duration = duration - (start - last_end)
                        # Case end of the day
                        if time_segment == worktime[-1]:
                            # We check if there is free slot for remaining duration just at the start of the day after
                            tomorrow = current_day + relativedelta(days=1, hour=0, minute=0, second=0)
                            tomorrow_worktime = self.employee_id.get_horaires_date(tomorrow.date())[self.employee_id.id]
                            tomorrow_interventions = intervention_obj.with_context(virtual_id=True).search([
                                ('employee_ids', 'in', self.employee_id.id),
                                ('date', '<=', fields.Date.to_string(tomorrow.date())),
                                ('date_deadline', '>=', fields.Date.to_string(tomorrow.date())),
                                ('state', 'not in', ('cancel', 'postponed'))], order='date')
                            if tomorrow_worktime:
                                tomorrow_start_hour = tomorrow_worktime[0][0]
                                tomorrow_timeline = self.env['of.planning.tournee'].\
                                    _get_employee_day_unavailability_timeline(
                                        fields.Date.to_string(tomorrow.date()), tomorrow_interventions,
                                        tomorrow_worktime)
                                tomorrow_last_end = 0
                                for tomorrow_start, tomorrow_end in tomorrow_timeline:
                                    if tomorrow_last_end == tomorrow_start_hour and \
                                            tomorrow_start - tomorrow_last_end >= remaining_duration:
                                        # Check if there is no other intervention with forced dates
                                        hours, minutes = float_2_heures_minutes(last_end)
                                        target_start_date = current_day + relativedelta(
                                            hour=int(hours), minute=int(minutes))
                                        target_start_date_utc = tz.localize(target_start_date).astimezone(pytz.utc)
                                        hours, minutes = float_2_heures_minutes(
                                            tomorrow_start_hour + remaining_duration)
                                        target_end_date = tomorrow + relativedelta(
                                            hour=int(hours), minute=int(minutes))
                                        target_end_date_utc = tz.localize(target_end_date).astimezone(pytz.utc)
                                        if not intervention_obj.with_context(virtual_id=True).search([
                                                ('employee_ids', 'in', self.employee_id.id),
                                                ('date', '<', fields.Datetime.to_string(target_end_date_utc)),
                                                ('date_deadline', '>', fields.Datetime.to_string(
                                                    target_start_date_utc)),
                                                ('state', 'not in', ('cancel', 'postponed'))]):
                                            start_time = last_end
                                            break
                                    if tomorrow_end > tomorrow_last_end:
                                        tomorrow_last_end = tomorrow_end
                                if start_time:
                                    # We found a free slot on 2 days, break
                                    break
                        # Case day break
                        else:
                            # We check if there is free slot for remaining duration just after the day break
                            next_timeline = filter(lambda time: time[0] >= end, day_timeline)
                            if next_timeline:
                                next_timeline = next_timeline[0]
                                if next_timeline[0] - end >= remaining_duration:
                                    # Check if there is no other intervention with forced dates
                                    hours, minutes = float_2_heures_minutes(last_end)
                                    target_start_date = current_day + relativedelta(
                                        hour=int(hours), minute=int(minutes))
                                    target_start_date_utc = tz.localize(target_start_date).astimezone(pytz.utc)
                                    hours, minutes = float_2_heures_minutes(
                                        end + remaining_duration)
                                    target_end_date = current_day + relativedelta(
                                        hour=int(hours), minute=int(minutes))
                                    target_end_date_utc = tz.localize(target_end_date).astimezone(pytz.utc)
                                    if not intervention_obj.with_context(virtual_id=True).search([
                                            ('employee_ids', 'in', self.employee_id.id),
                                            ('date', '<', fields.Datetime.to_string(target_end_date_utc)),
                                            ('date_deadline', '>', fields.Datetime.to_string(target_start_date_utc)),
                                            ('state', 'not in', ('cancel', 'postponed'))]):
                                        start_time = last_end
                                        # We found a free slot around day break, break
                                        break
                if end > last_end:
                    last_end = end

            if start_time:
                # We found a free slot, intervention creation for current service
                service = services_to_process[0]
                hours, minutes = float_2_heures_minutes(start_time)
                start_date = current_day + relativedelta(hour=int(hours), minute=int(minutes))
                start_date_utc = tz.localize(start_date).astimezone(pytz.utc)

                if service.address_id:
                    name = [service.address_id.name_get()[0][1]]
                    for field in ('zip', 'city'):
                        val = getattr(service.address_id, field)
                        if val:
                            name.append(val)
                name = name and " ".join(name) or "Intervention"

                values = {
                    'partner_id': service.partner_id.id,
                    'address_id': service.address_id.id,
                    'tache_id': service.tache_id.id,
                    'template_id': service.template_id.id,
                    'service_id': service.id,
                    'employee_ids': [(4, self.employee_id.id)],
                    'tag_ids': [(4, tag.id) for tag in service.tag_ids],
                    'date': fields.Datetime.to_string(start_date_utc),
                    'duree': service.duree,
                    'name': name,
                    'user_id': self._uid,
                    'company_id': service.company_id.id,
                    'description_interne': service.note,
                    'order_id': service.order_id.id,
                    'origin_interface': u"Générer RDV depuis DI",
                    'flexible': service.tache_id.flexible,
                }

                intervention = intervention_obj.create(values)
                if group_flex:
                    others = intervention.get_overlapping_intervention().filtered('flexible')
                    if others:
                        others.button_postponed()
                intervention.onchange_company_id()
                intervention.with_context(of_import_service_lines=True)._onchange_service_id()
                intervention.with_context(of_import_service_lines=True)._onchange_tache_id()
                intervention.with_context(of_import_service_lines=True).onchange_template_id()
                new_interventions += intervention

                # We remove service from services to process
                services_to_process -= service
                # We place the current date just after the new intervention
                current_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.from_string(intervention.date_deadline))
            else:
                # No free slot this day, we change the current date to the day after
                current_date = current_date + relativedelta(days=1, hour=0, minute=0, second=0)

        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        context = safe_eval(action['context'])
        context['force_date_start'] = new_interventions[0].date_date
        action['context'] = str(context)
        action['domain'] = [('id', 'in', new_interventions.ids)]
        return action


class OFServiceCreateInterventionLineWizard(models.TransientModel):
    _name = 'of.service.create.intervention.line.wizard'
    _description = u"Ligne d'assistant de création de RDV depuis les DI"
    _order = 'sequence'

    wizard_id = fields.Many2one(comodel_name='of.service.create.intervention.wizard', string=u"Wizard")
    sequence = fields.Integer(string=u"Séquence", default=10)
    service_id = fields.Many2one(comodel_name='of.service', string=u"DI", required=True)
    service_number = fields.Char(string=u"Numéro", related='service_id.number')
    service_titre = fields.Char(string=u"Titre", related='service_id.titre')
    service_partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Partenaire", related='service_id.partner_id')
    service_address_zip = fields.Char(string=u"Code postal", related='service_id.address_zip')
    service_address_city = fields.Char(string=u"Ville", related='service_id.address_city')
    service_task_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche", related='service_id.tache_id')
    service_duration = fields.Float(string=u"Durée", related='service_id.duree')
