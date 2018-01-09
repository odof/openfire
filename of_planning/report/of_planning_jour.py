# -*- coding: utf-8 -*-
from odoo.report import report_sxw
from odoo import fields
from datetime import datetime

class OfPlanningJour(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(OfPlanningJour, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_titre': self.get_titre,
            'get_line': self.get_line,
            'get_heure': self.get_heure,
            'get_client': self.get_client,
            'get_local_datetime': self.get_local_datetime,
            })

    def get_local_datetime(self):
        user = self.localcontext['user']
        if not user._context.get('tz'):
            user = user.with_context(tz='Europe/Paris')
        date = fields.Datetime.context_timestamp(user, datetime.now())
        date_str = fields.Datetime.to_string(date)
        return self.formatLang(date_str, date_time=True)

    def get_titre(self, equipe):
        date_date = fields.Date.from_string(self.objects.date_start)

        date_month = date_date.strftime("%B").decode("utf-8").capitalize()
        date_weekday = date_date.strftime("%A")
        title = "%s - Planning du %s %s %s %s" % (equipe.name, date_weekday, date_date.day, date_month, date_date.year)
        return title

    def get_line(self, equipe):
        intervention_obj = self.env['of.planning.intervention']

        date_start = self.objects.date_start

        # Recherche des taches de cette journee, sauf brouillons, reportees ou annulees
        domain = [('date_deadline', '>=', date_start), ('date', '<=', date_start), ('equipe_id', '=', equipe.id), ('state', 'in', ('draft', 'confirm', 'done'))]
        interventions = intervention_obj.search(domain, order='date')
        return interventions

    def get_heure(self, line):
        date_datetime_local = fields.Datetime.context_timestamp(line, fields.Datetime.from_string(line.date))
        planning_datetime_local = fields.Datetime.context_timestamp(line, fields.Datetime.from_string(self.datas['form']['date_start']))

        if date_datetime_local.day != planning_datetime_local.day:
            int_date_hour = int(line.hor_md)
            int_date_min = int(round((line.hor_md - int_date_hour) * 60, 0))
        else:
            int_date_hour = datetime.time(date_datetime_local).hour
            int_date_min = datetime.time(date_datetime_local).minute

        return "%02d:%02d" % (int_date_hour, int_date_min)

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

report_sxw.report_sxw('report.of_planning.of_planning_jour', 'of.planning.report', 'addons/of_planning/report/of_planning_jour.rml', parser=OfPlanningJour, header=False)
