# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    # Questionnaires
    fi_surveys = fields.Boolean(string="QUESTIONNAIRE")

    # Questionnaires
    ri_surveys = fields.Boolean(string="QUESTIONNAIRE")
