# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    accounting_company_id = fields.Many2one(
        comodel_name='res.company',
        related="company_id.accounting_company_id",
        readonly=True
    )
    writeoff_account_id = fields.Many2one(
        domain="[('deprecated', '=', False), ('company_id', '=', accounting_company_id)]"
    )

    def post(self):
        # Correction du code de tiers récupéré par Odoo sur la société courante de l'utilisateur
        # au lieu de celle du paiement
        for company in self.mapped('company_id'):
            payments = self.filtered(lambda p: p.company_id == company).with_context(force_company=company.id)
            super(AccountPayment, payments).post()
        # company_id n'est pas un champ obligatoire dans les paiements
        payments = self.filtered(lambda p: not p.company_id)
        return super(AccountPayment, payments).post()
