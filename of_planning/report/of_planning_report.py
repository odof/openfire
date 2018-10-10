# -*- coding: utf-8 -*-

import time
from datetime import timedelta, datetime
from odoo import models, fields, api

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

    def get_interventions(self, equipe_ids, date_inter=None):
        intervention_obj = self.env['of.planning.intervention']

        self.set_context(date_inter)

        date_start = fields.Date.to_string(self.localcontext['date_start'])
        date_stop = fields.Date.to_string(self.localcontext['date_stop'])

        domain = [('date_deadline', '>=', date_start), ('date', '<=', date_stop), ('equipe_id', 'in', equipe_ids), ('state', 'in', ('draft', 'confirm', 'done'))]
        interventions = intervention_obj.search(domain, order='equipe_id, date')

        res = []
        days = range(5)

        for interv in interventions:
            # Datetime UTC
            dt_utc = datetime.strptime(interv.date, "%Y-%m-%d %H:%M:%S")
            # Datetime local
            dt_local = fields.Datetime.context_timestamp(interv, dt_utc)

            day = dt_local.weekday()
            if day not in days:
                days.append(day)

            if not res or res[-1][0] != interv.equipe_id.name:
                res.append([interv.equipe_id.name, {}])

            heure = dt_local.strftime("%H:%M")

            equipe_jours_dict = res[-1][1]
            equipe_jours_dict.setdefault(day, [False, []])[1].append((heure, interv))
            if interv.tache_id.imp_detail:
                equipe_jours_dict[day][0] = True
        days.sort()

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
