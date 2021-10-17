# -*- coding: utf-8 -*-

import time
from datetime import timedelta, datetime
from collections import OrderedDict
from odoo import models, fields, api
from odoo.addons.of_utils.models.of_utils import format_date, float_2_heures_minutes


class OFHoraireSegmentWizard(models.TransientModel):
    _inherit = 'of.horaire.segment.wizard'

    # @todo: générer la liste des interventions concernées
    intervention_ids = fields.Many2many('of.planning.intervention', string=u"Interventions concernées")


class PlanningImpressionWizard(models.TransientModel):
    _name = "of_planning.impression_wizard"

    type = fields.Selection([
        ('day', u"Journée"),
        ('week', u"Semaine"),
        ('week2', u"Général semaine"),
    ], string="Type", required=True, default='day')
    date_start = fields.Date(string=u"Date", required=True)
    date_stop = fields.Date(string=u"Date de fin", compute='_compute_date_stop')
    employee_ids = fields.Many2many(
        'hr.employee', string=u"Employés",
        domain="['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True),"
               "('of_impression_planning', '=', True)]")

    @api.depends('type', 'date_start')
    def _compute_date_stop(self):
        for wizard in self:
            if wizard.type == 'day':
                wizard.date_stop = wizard.date_start
            else:
                date_start_da = fields.Date.from_string(wizard.date_start)
                date_stop_da = date_start_da + timedelta(days=7)
                wizard.date_stop = fields.Date.to_string(date_stop_da)

    @api.onchange('type')
    def check_change(self):
        if self.type and self.type == 'week2':
            employee_ids = self.env['hr.employee'].search([
                ('of_impression_planning', '=', True)
            ])
            self.employee_ids = [(6, 0, employee_ids._ids)]
            date_start = self.date_start or fields.Date.context_today(self)
            date_start = fields.Date.from_string(date_start)

            week_day = date_start.isocalendar()[2]
            if week_day > 1:
                date_start -= timedelta(days=week_day-1)

            self.date_start = date_start
        else:
            self.employee_ids = [(5, 0, 0)]

    @api.multi
    def button_print(self):
        self.ensure_one()
        if self.type == 'day':
            return self.env['report'].get_action(self, 'of_planning.report_of_planning_jour')
        elif self.type == 'week':
            return self.env['report'].get_action(self, 'of_planning.report_of_planning_semaine')
        else:
            return self.env['report'].get_action(self, 'of_planning.report_of_planning_general_semaine')

    @api.multi
    def get_title(self, employee_id=False):
        self.ensure_one()
        date_start_da = fields.Date.from_string(self.date_start)
        date_stop_da = fields.Date.from_string(self.date_stop)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        title = u""
        if self.type == 'day':
            title = u"%s - Planning d'intervention du %s%s" % (
                employee.name,
                date_start_da.day,
                date_start_da.strftime(" %B %Y").decode('utf-8'))
        elif self.type == 'week':
            title = u"Planning d'intervention - %s<br/>Semaine %s du %s%s au %s%s" % (
                employee.name,
                date_start_da.isocalendar()[1],
                date_start_da.day,
                date_start_da.strftime(" %B").decode('utf-8'),
                date_stop_da.day,
                date_stop_da.strftime(" %B %Y").decode('utf-8'))
        elif self.type == 'week2':
            title = u"Planning d'intervention - Semaine %s du %s%s au %s%s" % (
                date_start_da.isocalendar()[1],
                date_start_da.day,
                date_start_da.strftime(" %B").decode('utf-8'),
                date_stop_da.day,
                date_stop_da.strftime(" %B %Y").decode('utf-8'))
        return title

    def get_interventions_one(self, employee_id):
        intervention_obj = self.env['of.planning.intervention']

        # Toutes les poses de la semaine, sauf annulées ou reportées
        domain = [('date_deadline', '>=', self.date_start), ('date', '<=', self.date_stop),
                  ('employee_ids', 'in', employee_id),
                  ('state', 'not in', ('cancel', 'postponed'))]
        interventions = intervention_obj.search(domain, order='date')
        return interventions

    def get_interventions_all(self):
        intervention_obj = self.env['of.planning.intervention']

        date_start_da = fields.Date.from_string(self.date_start)
        date_stop_da = fields.Date.from_string(self.date_stop)

        temp = OrderedDict()
        days = range(5)  # @todo: jours travaillés
        employees = self.employee_ids.sorted('sequence')

        for employee in employees:
            domain = [('date_deadline', '>=', self.date_start), ('date', '<=', self.date_stop),
                      ('employee_ids', 'in', employee.id),
                      ('state', 'not in', ('cancel', 'postponed'))]
            interventions = intervention_obj.search(domain, order='date')

            for interv in interventions:
                # Datetime UTC début
                date_start_utc_dt = datetime.strptime(interv.date, "%Y-%m-%d %H:%M:%S")
                # Datetime local début
                date_start_locale_dt = fields.Datetime.context_timestamp(interv, date_start_utc_dt)
                # Datetime UTC fin
                date_stop_utc_dt = datetime.strptime(interv.date_deadline, "%Y-%m-%d %H:%M:%S")
                # Datetime local fin
                date_stop_locale_dt = fields.Datetime.context_timestamp(interv, date_stop_utc_dt)

                date_da = date_start_locale_dt.date()
                date_deadline_da = date_stop_locale_dt.date()
                date_current_da = date_da
                while date_current_da <= date_deadline_da:
                    # Cette date est en dehors de la semaine d'évaluation
                    if not (date_start_da <= date_current_da <= date_stop_da):
                        date_current_da += timedelta(days=1)
                        continue

                    # premier jour de l'intervention : l'heure est l'heure de début de l'intervention
                    if date_current_da == date_da:
                        heure = date_start_locale_dt.strftime("%H:%M")
                    # jour suivant : l'heure est celle du début de la journée de l'employé
                    else:
                        horaires_du_jour = interv.employee_ids.get_horaires_date(date_current_da)
                        if horaires_du_jour[employee.id]:
                            # heure de début du premier créneau de la journée
                            heure = u"%02d:%02d" % float_2_heures_minutes(horaires_du_jour[employee.id][0][0])
                        else:
                            heure = -1
                    if heure >= 0.0:
                        day = date_current_da.weekday()
                        if day not in days:
                            days.append(day)
                        if not temp or employee.name not in temp:
                            temp[employee.name] = {}
                        employee_jours_dict = temp[employee.name]
                        employee_jours_dict.setdefault(day, [False, []])[1].append((heure, interv))
                        if interv.tache_id.imp_detail:
                            employee_jours_dict[day][0] = True
                    date_current_da += timedelta(days=1)
            days.sort()

        res = [[key, temp[key]] for key in temp.keys()]
        for _, intervs_dict in res:
            for day, (imp_detail, intervs) in intervs_dict.iteritems():
                if imp_detail:
                    intervs_dict[day] = [
                        (heure, self.get_intervention_detail(interv), self.get_interv_state_display(interv))
                        for heure, interv in intervs]
                else:
                    maxi = {}
                    for _, j in intervs:
                        if j.tache_id in maxi:
                            maxi[j.tache_id] += 1
                        else:
                            maxi[j.tache_id] = 1

                    tache_max_use = max(maxi, key=lambda k: maxi[k])
                    intervs_dict[day] = [(False, tache_max_use.name, False)]

        if res:
            return [res, days]
        else:
            return [[], []]

    def get_intervention_detail(self, intervention):
        return intervention.partner_id and intervention.partner_id.name or u""

    def get_interv_state_display(self, intervention):
        return intervention.state == 'confirm' and u'<span class="fa fa-check"/> ' or u''

    def get_columns(self, intervention):
        # heure, client, tâche, description
        res = []
        if self.type == 'day':
            res.append(self.get_heure(intervention))
        elif self.type == 'week':
            res.append(self.get_date_et_heure(intervention))
        res.append(self.get_client(intervention))
        res.append(intervention.tache_id.name)
        res.append(self.get_description(intervention))
        return res

    def get_heure(self, intervention):
        date_datetime_local = fields.Datetime.context_timestamp(
            intervention, fields.Datetime.from_string(intervention.date))
        return "%02d:%02d" % (date_datetime_local.hour, date_datetime_local.minute)

    def get_date_et_heure(self, intervention):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        date_start_datetime_local = fields.Datetime.context_timestamp(
            intervention, fields.Datetime.from_string(intervention.date))
        date_start_local = date_start_datetime_local.date()
        date_stop_datetime_local = fields.Datetime.context_timestamp(
            intervention, fields.Datetime.from_string(intervention.date_deadline))
        date_stop_local = date_stop_datetime_local.date()
        if date_start_local != date_stop_local:
            res = u"du %s %s à %02d:%02d<br/>au %s %s à %02d:%02d" % (
                self.int_to_day(date_start_local.weekday()),
                format_date(date_start_local, lang, with_year=False),
                date_start_datetime_local.hour,
                date_start_datetime_local.minute,
                self.int_to_day(date_stop_local.weekday()),
                format_date(date_stop_local, lang, with_year=False),
                date_stop_datetime_local.hour,
                date_stop_datetime_local.minute,
            )
        else:
            res = u"le %s %s<br/>de %02d:%02d à %02d:%02d" % (
                self.int_to_day(date_start_local.weekday()),
                format_date(date_start_local, lang, with_year=False),
                date_start_datetime_local.hour,
                date_start_datetime_local.minute,
                date_stop_datetime_local.hour,
                date_stop_datetime_local.minute,
            )
        return res

    def int_to_day(self, day_int):
        self.ensure_one()
        # planning semaine
        if self.type == 'week':
            return ("Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim.")[day_int]
        # planning général semaine
        return ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")[day_int]

    def get_client(self, line):
        if not line.address_id:
            return ""
        address = line.address_id
        city_vals = [s for s in (address.zip, address.city) if s]
        name = self.get_interv_state_display(line)
        name += address.name or address.parent_name or ''
        partner_vals = [s for s in (
            name,
            address.street,
            address.street2,
            " ".join(city_vals),
            address.phone,
            address.mobile,
            address.fax,
        ) if s]
        return "<br/>".join(partner_vals)

    def get_description(self, line):
        if not line.description:
            return u""
        return line.description.replace('<br>', '\n').replace('<br/>', '\n').replace('<p>', '').replace('</p>', '\n') \
            .replace('<p/>', '\n').replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '') \
            .replace('<u>', '').replace('</u>', '')
