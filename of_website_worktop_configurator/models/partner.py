# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_worktop_configurator_contact = fields.Boolean(string=u"Contact calculateur")
    of_worktop_configurator_responsible = fields.Boolean(string=u"Responsable calculateur")

    @api.onchange('of_worktop_configurator_contact')
    def _onchange_of_worktop_configurator_contact(self):
        if not self.of_worktop_configurator_contact:
            self.of_worktop_configurator_responsible = False
