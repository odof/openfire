# -*- coding: utf-8 -*-

from odoo import models, fields


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    fi_order_restant_du = fields.Boolean(string=u"Restant dû")
    ri_order_restant_du = fields.Boolean(string=u"Restant dû")
