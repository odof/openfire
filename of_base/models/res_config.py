# -*- coding: utf-8 -*-

from odoo import fields, models


class OFConnectorConfigSettings(models.TransientModel):
    _name = 'of.connector.config.settings'
    _inherit = 'res.config.settings'
    _description = 'Configuration des connecteurs'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
