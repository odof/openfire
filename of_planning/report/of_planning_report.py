# -*- coding: utf-8 -*-

import time
from datetime import timedelta, datetime
from odoo import models, fields, api
from odoo.addons.of_utils.models.of_utils import format_date


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

        title = "Planning d'intervention - Semaine %s du %s%s au %s%s" % (date_start.isocalendar()[1],
                                                                          date_start.day,
                                                                          date_start.strftime(" %B"),
                                                                          date_stop.day,
                                                                          date_stop.strftime(" %B %Y"))
        return title

    def get_dates(self, date_start=None):
        self.set_context(date_start)
        date_start_date = self.localcontext['date_start']
        date_stop_date = self.localcontext['date_stop']

        date_debut = date_start_date
        date_fin = date_stop_date
        return (date_debut, date_fin)

    def get_interventions(self, employee_ids, date_inter=None):
        intervention_obj = self.env['of.planning.intervention']

        self.set_context(date_inter)

        date_start = fields.Date.to_string(self.localcontext['date_start'])
        date_stop = fields.Date.to_string(self.localcontext['date_stop'])

        domain = [('date_deadline', '>=', date_start), ('date', '<=', date_stop),
                  ('employee_ids', 'in', employee_ids),
                  ('state', 'in', ('draft', 'confirm', 'done', 'unfinished'))]
        interventions = intervention_obj.search(domain, order='date')

        temp = {}
        days = range(5) # @todo: jours travaillés

        for interv in interventions:
            # Datetime UTC
            date_utc_str = datetime.strptime(interv.date, "%Y-%m-%d %H:%M:%S")
            # Datetime local
            date_locale_dt = fields.Datetime.context_timestamp(interv, date_utc_str)

            day = date_locale_dt.weekday()
            if day not in days:
                days.append(day)

            heure = date_locale_dt.strftime("%H:%M")
            for employee in interv.employee_ids:
                if not temp or employee.name not in temp:
                    temp[employee.name] = {}
                employee_jours_dict = temp[employee.name]
                employee_jours_dict.setdefault(day, [False, []])[1].append((heure, interv))
                if interv.tache_id.imp_detail:
                    employee_jours_dict[day][0] = True
        days.sort()

        res = [[key, temp[key]] for key in temp.keys()]
        for _, intervs_dict in res:
            for day, (imp_detail, intervs) in intervs_dict.iteritems():
                if imp_detail:
                    intervs_dict[day] = [(heure, interv.partner_id.name or '', interv.state == 'confirm') for heure, interv in intervs]
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

        title = "Planning d'intervention - %s<br/>Semaine %s du %s%s au %s%s" % (
            employee.name,
            date_start.isocalendar()[1],
            date_start.day,
            date_start.strftime(" %B"),
            date_stop.day,
            date_stop.strftime(" %B %Y"))
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
        res.append(self.get_date(intervention))
        res.append(self.get_heure(intervention))
        res.append(self.get_client(intervention))
        res.append(intervention.tache_id.name)
        res.append(self.get_description(intervention))
        return res

    def get_date(self, intervention):
        date_datetime_local = fields.Datetime.context_timestamp(
            intervention, fields.Datetime.from_string(intervention.date))
        date_local = date_datetime_local.date()
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        return format_date(date_local, lang)

    def get_heure(self, intervention):
        date_datetime_local = fields.Datetime.context_timestamp(
            intervention, fields.Datetime.from_string(intervention.date))
        return "%02d:%02d" % (date_datetime_local.hour, date_datetime_local.minute)

    def get_client(self, line):
        if not line.address_id:
            return ""
        address = line.address_id
        city_vals = [s for s in (address.zip, address.city) if s]
        name = u""
        if line.state == 'confirm':
            name += u'<i class="fa fa-check"/> '
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

    def get_description(self, line):
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
        if week_day > 1:
            date_start_date -= timedelta(days=week_day - 1)
        self.localcontext = {}
        self.localcontext['date_start'] = date_start_date
        self.localcontext['date_stop'] = date_start_date

    @api.multi
    def get_title(self, employee_id, date_inter=None):
        self.set_context(date_inter)

        date_start = self.localcontext['date_start']
        employee = self.env['hr.employee'].sudo().browse(employee_id)

        title = "%s - Planning d'intervention du %s%s" % (
            employee.name,
            date_start.day,
            date_start.strftime(" %B %Y"))
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
        name = u""
        if line.state == 'confirm':
            name += u'<i class="fa fa-check"/> '
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

    def get_description(self, line):
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
