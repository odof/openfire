# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import time
import locale
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

REPORT_TYPES = [('day',u"Journée")]

class OfPlanningReport(models.TransientModel):
    _name = 'of.planning.report'

    type = fields.Selection([
        ('day',u"Journée"),
#        ('week', "Semaine"),
#        ('week2', u"Semaine (condensé)")
    ], string="Type", required=True, default='day')
    date_start = fields.Date("Début")
    equipe_ids = fields.Many2many('of.planning.equipe', string=u"Équipes")

    @api.multi
    def button_print(self):
        tmp = self.read()[0]
        data = {
            'ids' : self._ids,
            'model' : self._name,
            'form' : tmp,
        }

        return {
            'type' : 'ir.actions.report.xml',
            'report_name':'of_planning.of_planning_jour',
            'datas' : data,
        }

        next_state = data['model']

        return next_state
