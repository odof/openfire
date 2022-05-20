# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche de projet")
