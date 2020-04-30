# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OfPlanningIntervention(models.Model):
    _name = 'of.planning.intervention'
    _inherit = ['of.planning.intervention', 'of.crm.stage.auto.update']

    opportunity_id = fields.Many2one(
        comodel_name='crm.lead', string=u"Opportunité associée",
        domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")
