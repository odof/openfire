# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    # SAV
    fi_sav = fields.Boolean(string="SAV")

    # SAV
    ri_sav = fields.Boolean(string="SAV")
