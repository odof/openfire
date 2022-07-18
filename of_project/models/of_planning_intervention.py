# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche de projet")
