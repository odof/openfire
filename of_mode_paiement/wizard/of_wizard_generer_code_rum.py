# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfGenererCodeRumWizard(models.TransientModel):
    _name = 'of.generer.code.rum.wizard'

    partner_bank_id = fields.Many2one('res.partner.bank', string=u"Compte bancaire")

    @api.multi
    def validate(self):
        if self.partner_bank_id:
            self.partner_bank_id.generer_code_rum()

        return True
