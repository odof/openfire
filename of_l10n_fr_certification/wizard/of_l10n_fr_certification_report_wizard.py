# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time

class OfImpressionWizard(models.TransientModel):
    _name = "of.impression.wizard"

    # récupérer la listes des sociétés
    company_id = fields.Many2one("res.company", string=u"Société", required=True)

    @api.model
    def get_date(self):
        return time.strftime("%d/%m/%Y")

    @api.multi
    def button_print(self):
        return self.env['report'].get_action(self, 'of_l10n_fr_certification.of_report_attestation_certification')
