# -*- coding: utf-8 -*-

from odoo import api, fields, models
class OfInterventionSettings(models.TransientModel):
    _name = 'of.intervention.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)

