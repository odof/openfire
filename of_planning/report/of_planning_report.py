# -*- coding: utf-8 -*-

import time
from datetime import timedelta, datetime
from collections import OrderedDict
from odoo import models, fields, api
from odoo.addons.of_utils.models.of_utils import format_date, float_2_heures_minutes


class ReportPlanningGeneralSemaine(models.AbstractModel):
    _name = "report.of_planning.report_planning_general_semaine"

    @api.model
    def set_context(self, date_start=None):
        # Ajout des dates de debut et de fin de la recherche dans localcontext

        if date_start is not None:
            date_start_date = fields.Date.from_string(date_start)
        else:
            date_start_date = fields.Date.context_today(self)

        week_day = date_start_date.isocalendar()[2]
        if week_day > 1:
            date_start_date -= timedelta(days=week_day-1)
        self.localcontext = {}
        self.localcontext['date_start'] = date_start_date
        self.localcontext['date_stop'] = date_start_date + timedelta(days=6)

    @api.multi
    def get_title(self, date_inter=None):

        self.set_context(date_inter)

        date_start = self.localcontext['date_start']
        date_stop = self.localcontext['date_stop']

        title = u"Planning d'intervention - Semaine %s du %s%s au %s%s" % (date_start.isocalendar()[1],
                                                                           date_start.day,
                                                                           date_start.strftime(" %B").decode('utf-8'),
                                                                           date_stop.day,
                                                                           date_stop.strftime(" %B %Y").decode('utf-8'))
        return title

    def get_interventions(self, employee_ids, date_inter=None):
        intervention_obj = self.env['of.planning.intervention']

        self.set_context(date_inter)

        date_start = fields.Date.to_string(self.localcontext['date_start'])
        date_start_da = self.localcontext['date_start']
        date_stop = fields.Date.to_string(self.localcontext['date_stop'])
        date_stop_da = self.localcontext['date_stop']

        temp = OrderedDict()
        days = range(5)  # @todo: jours travaillés
        employee_obj = self.env['hr.employee']
        employees = employee_obj.browse(employee_ids).sorted('sequence')

        for employee in employees:
            domain = [('date_deadline', '>=', date_start), ('date', '<=', date_stop),
                      ('employee_ids', 'in', employee.id),
                      ('state', 'in', ('draft', 'confirm', 'done', 'unfinished'))]
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
                    for _, j in intervs :
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
        return intervention.state == 'confirm' and '<span class="fa fa-check"/>' or ''

    def int_to_day(self, day_int):
        return ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")[day_int]

    @api.model
    def render_html(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        docargs = {
            'doc_ids': docids or self._ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_interventions': self.get_interventions,
            'get_title': self.get_title,
            'int_to_day': self.int_to_day,
        }
        return self.env['report'].render('of_planning.report_planning_general_semaine', docargs)


class ReportPlanningSemaine(models.AbstractModel):
    _name = "report.of_planning.report_planning_semaine"

    @api.model
    def set_context(self, date_start=None):
        # Ajout des dates de debut et de fin de la recherche dans localcontext

        if date_start is not None:
            date_start_date = fields.Date.from_string(date_start)
        else:
            date_start_date = fields.Date.from_string(fields.Date.context_today(self))

        week_day = date_start_date.isocalendar()[2]
        if week_day > 1:
            date_start_date -= timedelta(days=week_day-1)
        self.localcontext = {}
        self.localcontext['date_start'] = date_start_date
        self.localcontext['date_stop'] = date_start_date + timedelta(days=6)

    @api.multi
    def get_title(self, employee_id, date_inter=None):
        self.set_context(date_inter)

        date_start = self.localcontext['date_start']
        date_stop = self.localcontext['date_stop']
        employee = self.env['hr.employee'].sudo().browse(employee_id)

        title = u"Planning d'intervention - %s<br/>Semaine %s du %s%s au %s%s" % (
            employee.name,
            date_start.isocalendar()[1],
            date_start.day,
            date_start.strftime(" %B").decode('utf-8'),
            date_stop.day,
            date_stop.strftime(" %B %Y").decode('utf-8'))
        return title

    def get_interventions(self, employee_id, date_start=None):
        self.set_context(date_start)
        intervention_obj = self.env['of.planning.intervention']

        # changer le type a string pour search
        date_start = fields.Date.to_string(self.localcontext['date_start'])
        date_stop = fields.Date.to_string(self.localcontext['date_stop'])

        # Toutes les poses de la semaine, sauf annulées ou reportées
        domain = [('date_deadline', '>=', date_start), ('date', '<=', date_stop),
                  ('employee_ids', 'in', employee_id),
                  ('state', 'in', ('draft', 'confirm', 'done', 'unfinished'))]
        interventions = intervention_obj.search(domain, order='date')
        return interventions

    def get_columns(self, intervention):
        # date, heure, client, tâche, description
        res = []
        res.append(self.get_date_et_heure(intervention))
        res.append(self.get_client(intervention))
        res.append(intervention.tache_id.name)
        res.append(self.get_description(intervention))
        return res

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
        return ("Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim.")[day_int]

    def get_client(self, line):
        if not line.address_id:
            return ""
        address = line.address_id
        city_vals = [s for s in (address.zip, address.city) if s]
        name = self.get_interv_state_display(line)
        name += address.name
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

    def get_interv_state_display(self, intervention):
        return intervention.state == 'confirm' and u'<span class="fa fa-check"/> ' or u''

    def get_description(self, line):
        if not line.description:
            return u""
        return line.description.replace('<br>', '\n').replace('<br/>', '\n').replace('<p>', '').replace('</p>', '\n')\
            .replace('<p/>', '\n').replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')\
            .replace('<u>', '').replace('</u>', '')

    @api.model
    def render_html(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        docargs = {
            'doc_ids': docids or self._ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_interventions': self.get_interventions,
            'get_columns': self.get_columns,
            'get_title': self.get_title,
        }
        return self.env['report'].render('of_planning.report_planning_semaine', docargs)


class ReportPlanningJour(models.AbstractModel):
    _name = "report.of_planning.report_planning_jour"

    @api.model
    def set_context(self, date_start=None):
        # Ajout des dates de debut et de fin de la recherche dans localcontext

        if date_start is not None:
            date_start_date = fields.Date.from_string(date_start)
        else:
            date_start_date = fields.Date.from_string(fields.Date.context_today(self))

        week_day = date_start_date.isocalendar()[2]
        self.localcontext = {}
        self.localcontext['date_start'] = date_start_date
        self.localcontext['date_stop'] = date_start_date

    @api.multi
    def get_title(self, employee_id, date_inter=None):
        self.set_context(date_inter)

        date_start = self.localcontext['date_start']
        employee = self.env['hr.employee'].sudo().browse(employee_id)

        title = u"%s - Planning d'intervention du %s%s" % (
            employee.name,
            date_start.day,
            date_start.strftime(" %B %Y").decode('utf-8'))
        return title

    def get_interventions(self, employee_id, date_start=None):
        self.set_context(date_start)
        intervention_obj = self.env['of.planning.intervention']

        # changer le type a string pour search
        date_start = fields.Date.to_string(self.localcontext['date_start'])
        date_stop = fields.Date.to_string(self.localcontext['date_stop'])

        # Toutes les poses de la semaine, sauf annulées ou reportées
        domain = [('date_deadline', '>=', date_start), ('date', '<=', date_stop),
                  ('employee_ids', 'in', employee_id),
                  ('state', 'in', ('draft', 'confirm', 'done', 'unfinished'))]
        interventions = intervention_obj.search(domain, order='date')
        return interventions

    def get_columns(self, intervention):
        # heure, client, tâche, description
        res = []
        res.append(self.get_heure(intervention))
        res.append(self.get_client(intervention))
        res.append(intervention.tache_id.name)
        res.append(self.get_description(intervention))
        return res

    def get_heure(self, intervention):
        date_datetime_local = fields.Datetime.context_timestamp(
            intervention, fields.Datetime.from_string(intervention.date))
        return "%02d:%02d" % (date_datetime_local.hour, date_datetime_local.minute)

    def get_client(self, line):
        if not line.address_id:
            return ""
        address = line.address_id
        city_vals = [s for s in (address.zip, address.city) if s]
        name = self.get_interv_state_display(line)
        name += address.name
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

    def get_interv_state_display(self, intervention):
        return intervention.state == 'confirm' and u'<span class="fa fa-check"/> ' or u''

    def get_description(self, line):
        if not line.description:
            return u""
        return line.description.replace('<br>', '\n').replace('<br/>', '\n').replace('<p>', '').replace('</p>', '\n')\
            .replace('<p/>', '\n').replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')\
            .replace('<u>', '').replace('</u>', '')

    @api.model
    def render_html(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        docargs = {
            'doc_ids': docids or self._ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_interventions': self.get_interventions,
            'get_columns': self.get_columns,
            'get_title': self.get_title,
        }
        return self.env['report'].render('of_planning.report_planning_jour', docargs)
