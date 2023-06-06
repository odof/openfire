# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfPlanningIntervention(models.Model):
    _name = 'of.planning.intervention'
    _inherit = ['of.planning.intervention', 'of.crm.stage.auto.update']

    opportunity_id = fields.Many2one(
        comodel_name='crm.lead', string=u"Opportunité", copy=False,
        domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")
