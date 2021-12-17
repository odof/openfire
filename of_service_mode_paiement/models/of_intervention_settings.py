# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    group_of_intervention_sepa = fields.Boolean(
        string=u"(OF) Prélèvements SEPA", implied_group='of_service_mode_paiement.group_of_intervention_sepa')

    @api.multi
    def set_group_of_intervention_sepa_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'group_of_intervention_sepa', self.group_of_intervention_sepa)
