# -*- coding: utf-8 -*-
from odoo.report import report_sxw
from odoo import fields
from datetime import datetime
from odoo.exceptions import UserError

class OfPlanningJour(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(OfPlanningJour, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_titre': self.get_titre,
            'get_line': self.get_line,
            'get_heure': self.get_heure,
            'get_client': self.get_client,
            'get_description': self.get_description,
            'get_local_datetime': self.get_local_datetime,
            })

    def get_local_datetime(self):
        user = self.localcontext['user']
        if not user._context.get('tz'):
            user = user.with_context(tz='Europe/Paris')
        date = fields.Datetime.context_timestamp(user, datetime.now())
        date_str = fields.Datetime.to_string(date)
        return self.formatLang(date_str, date_time=True)

    def get_titre(self, employee):
        date_date = fields.Date.from_string(self.objects.date_start)

        date_month = date_date.strftime("%B").decode("utf-8").capitalize()
        date_weekday = date_date.strftime("%A")
        title = "%s - Planning du %s %s %s %s" % (employee.name, date_weekday, date_date.day, date_month, date_date.year)
        return title

    def get_line(self, employee):
        intervention_obj = self.env['of.planning.intervention']

        date_start = self.objects.date_start

        # Recherche des tâches de cette journée, sauf reportées ou annulées
        domain = [('date_deadline', '>=', date_start), ('date', '<=', date_start),
                  ('employee_ids', 'in', employee.id),
                  ('state', 'in', ('draft', 'confirm', 'done', 'unfinished'))]
        interventions = intervention_obj.search(domain, order='date')
        return interventions

    def get_heure(self, line):
        """renvois l'heure de début de journée. En cas d'intervenants multiples renvois l'heure la plus tôt"""
        date_datetime_local = fields.Datetime.context_timestamp(line, fields.Datetime.from_string(line.date))
        planning_datetime_local = fields.Datetime.context_timestamp(line, fields.Datetime.from_string(self.datas['form']['date_start']))

        if date_datetime_local.day != planning_datetime_local.day:  # en cas d'intervention sur plusieurs jours
            if line.forcer_horaires:
                int_date_hour = int(line.hor_md)
                int_date_min = int(round((line.hor_md - int_date_hour) * 60, 0))
            else:
                employees = line.employee_ids
                planning_dat_local_str = fields.Date.to_string(planning_datetime_local)
                horaires_du_jour = employees.get_horaires_date(planning_dat_local_str)
                heure_debut_min = 24
                for employee_id in horaires_du_jour:
                    if len(horaires_du_jour[employee_id]) > 0 and horaires_du_jour[employee_id][0][0] < heure_debut_min:
                        heure_debut_min = horaires_du_jour[employee_id][0][0]
                int_date_hour = int(heure_debut_min)
                int_date_min = int(round((heure_debut_min - int_date_hour) * 60, 0))
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

    def get_description(self, line):
        return line.description.replace('<br>', '\n').replace('<br/>', '\n').replace('<p>', '').replace('</p>', '\n').replace('<p/>', '\n').replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '').replace('<u>', '').replace('</u>', '')

report_sxw.report_sxw('report.of_planning.of_planning_jour', 'of_planning.impression_wizard', 'addons/of_planning/report/of_planning_jour.rml', parser=OfPlanningJour, header=False)
