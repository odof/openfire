# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta

class PlanningImpressionWizard(models.TransientModel):
    _name = "of_planning.impression_wizard"

    type = fields.Selection([
        ('day', u"Journée"),
        ('week', u"Semaine"),
        ('week2', u"Général semaine"),
    ], string="Type", required=True, default='day')
    date_start = fields.Date("Date", required=True)
    equipe_ids = fields.Many2many('of.planning.equipe', string=u"Équipes")

    @api.onchange('type')
    def check_change(self):
        if self.type and self.type == 'week2' :
            equipe_ids = self.env['of.planning.equipe'].search([])
            self.equipe_ids = [(6, 0, equipe_ids._ids)]
            date_start = self.date_start or fields.Date.context_today(self)
            date_start = fields.Date.from_string(date_start)

            week_day = date_start.isocalendar()[2]
            if week_day > 1:
                date_start -= timedelta(days=week_day-1)

            self.date_start = date_start
        else :
            self.equipe_ids = [(5, 0, 0)]

    @api.multi
    def button_print(self):
        self.ensure_one()
        tmp = self.read()[0]
        if self.type == 'week2':
            data = {
                'ids': self.env.context.get('active_ids', []),
                'model': self.env.context.get('active_model', 'ir.ui.menu'),
                'form': tmp,
            }

            return self.env['report'].get_action(self, 'of_planning.report_planning_general_semaine', data=data)
        else:
            data = {
                'ids' : self._ids,
                'model' : self._name,
                'form' : tmp,
                'date_start': self.date_start,
            }

            report_type_name = {
                'day': 'of_planning.of_planning_jour',
                'week': 'of_planning.of_planning_semaine',
            }

            return {
                'type' : 'ir.actions.report.xml',
                'report_name': report_type_name[self.type],
                'datas' : data,
            }

