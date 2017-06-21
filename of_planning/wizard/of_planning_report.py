# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfPlanningReport(models.TransientModel):
    _name = 'of.planning.report'

    type = fields.Selection([
        ('day', u"Journée"),
        ('week', "Semaine"),
        # ('week2', u"Semaine (condensé)"),
    ], string="Type", required=True, default='day')
    date_start = fields.Date("Date")
    equipe_ids = fields.Many2many('of.planning.equipe', string=u"Équipes")

    @api.multi
    def button_print(self):
        tmp = self.read()[0]
        data = {
            'ids' : self._ids,
            'model' : self._name,
            'form' : tmp,
        }

        report_type_name = {
            'day': 'of_planning.of_planning_jour',
            'week': 'of_planning.of_planning_semaine',
            'week2': 'of_planning.of_planning_semaine_condense',
        }

        return {
            'type' : 'ir.actions.report.xml',
            'report_name': report_type_name[self.type],
            'datas' : data,
        }
