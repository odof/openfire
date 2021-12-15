# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfService(models.Model):
    _inherit = 'of.service'

    of_validite_sepa = fields.Selection(
        [("non_verifie", u"Non vérifiée"), ("non_valide", u"Non valide"), ("valide", u"Valide")],
        string=u"Validité du SEPA", readonly=True, required=True, default="non_verifie")
    of_date_verification_sepa = fields.Date(u'Date de vérification', readonly=True)

    @api.multi
    def verification_validite_sepa(self):
        """Action appelée pour vérifier la validité du SEPA"""
        for invoice in self:
            # On check également le commercial_partner_id car les comptes bancaires
            # peuvent être définis chez ce partenaire
            if any(bank.verification_validite() for bank in invoice.partner_id.bank_ids) \
                    or any(bank.verification_validite() for bank in invoice.partner_id.commercial_partner_id.bank_ids):
                invoice.of_validite_sepa = 'valide'
            else:
                invoice.of_validite_sepa = 'non_valide'
            invoice.of_date_verification_sepa = fields.Date.today()
        return True
