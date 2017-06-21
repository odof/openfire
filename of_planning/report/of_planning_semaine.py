# -*- coding: utf-8 -*-
from odoo.report import report_sxw
from datetime import datetime, timedelta
from odoo import fields

class OfPlanningSemaine(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(OfPlanningSemaine, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'get_titre': self.get_titre,
            'get_interventions': self.get_interventions,
            'get_date': self.get_date,
            'get_heure': self.get_heure,
            'get_client': self.get_client,
            'get_local_datetime': self.get_local_datetime,
            })

    def set_context(self, objects, data, ids, report_type=None):
        # Ajout des dates de debut et de fin de la recherche dans localcontext
        super(OfPlanningSemaine, self).set_context(objects, data, ids, report_type=report_type)

        date_start_date = fields.Date.from_string(self.objects.date_start)
        week_day = date_start_date.isocalendar()[2]
        if week_day > 1:
            date_start_date -= timedelta(days=week_day-1)

        self.localcontext['date_start'] = date_start_date
        self.localcontext['date_stop'] = date_start_date + timedelta(days=6)

    def get_local_datetime(self):
        user = self.localcontext['user']
        if not user._context.get('tz'):
            user = user.with_context(tz='Europe/Paris')
        date = fields.Datetime.context_timestamp(user, datetime.now())
        date_str = fields.Datetime.to_string(date)
        return self.formatLang(date_str, date_time=True)

    def get_titre(self, equipe):
        date_start_date = self.localcontext['date_start']
        date_stop_date = self.localcontext['date_stop']

        week_number = date_start_date.isocalendar()[1]

        date_start_extend = ""
        if date_start_date.year != date_stop_date.year:
            date_start_extend = date_start_date.strftime(" %B %Y")
        elif date_start_date.month != date_stop_date.month:
            date_start_extend = date_start_date.strftime(" %Y")

        title = "Planning des Interventions - %s - Semaine %s du %s%s au %s%s" % (equipe.name, week_number, date_start_date.day, date_start_extend, date_stop_date.day, date_stop_date.strftime(" %B %Y"))
        return title

    def get_interventions(self, equipe):
        intervention_obj = self.env['of.planning.intervention']

        # changer le type a string pour search
        date_start = fields.Date.to_string(self.localcontext['date_start'])
        date_stop = fields.Date.to_string(self.localcontext['date_stop'])

        # Toutes les poses de la semaine, sauf brouillons, annulees ou reportees
        domain = [('date_deadline', '>=', date_start), ('date', '<=', date_stop), ('equipe_id', '=', equipe.id), ('state', 'in', ('draft', 'confirm', 'done'))]
        interventions = intervention_obj.search(domain, order='date')
        return interventions

    def get_date(self, intervention):
        date_datetime_local = fields.Datetime.context_timestamp(intervention, fields.Datetime.from_string(intervention.date))
        date_local = date_datetime_local.date()
        return date_local

    def get_heure(self, intervention):
        date_datetime_local = fields.Datetime.context_timestamp(intervention, fields.Datetime.from_string(intervention.date))
        return "%02d:%02d" % (date_datetime_local.hour, date_datetime_local.minute)

    def get_client(self, line):
        if not line.address_id:
            return ""
        address = line.address_id
        city_vals = [s for s in (address.zip, address.city) if s]
        partner_vals = [s for s in (
            address.name,
            address.street,
            address.street2,
            " ".join(city_vals),
            address.phone,
            address.mobile,
            address.fax,
        ) if s]
        return "\n".join(partner_vals)

report_sxw.report_sxw('report.of_planning.of_planning_semaine', 'of.planning.report', 'addons/of_planning/report/of_planning_semaine.rml', parser=OfPlanningSemaine, header=False)
