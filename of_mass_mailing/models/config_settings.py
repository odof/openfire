# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api

class MassMailingConfiguration(models.TransientModel):
    _inherit = 'mass.mailing.config.settings'

    of_mass_mailing_limit = fields.Integer(string=u"(OF) Limite d'envoi de mail")

    @api.multi
    def set_default_of_mass_mailing_limit(self):
        self.env['ir.values'].set_default(
            'mass.mailing.config.settings', 'of_mass_mailing_limit', self.of_mass_mailing_limit)
