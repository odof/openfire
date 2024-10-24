# -*- coding: utf-8 -*-
from math import ceil

from odoo import api, fields, models


class OFContract(models.Model):
    _inherit = 'of.contract'

    @api.multi
    def copy_contract_vals(self, date_start, date_end, renewal):
        self.ensure_one()
        return {
            'type': self.type,
            'contract_type': self.contract_type,
            'reference': self.reference + " (copy)",
            'partner_id': self.partner_id.id,
            'date_souscription': self.date_souscription,
            'manager_id': self.manager_id.id,
            'recurring_invoicing_payment_id': self.recurring_invoicing_payment_id.id,
            'recurring_rule_type': self.recurring_rule_type,
            'journal_id': self.journal_id.id,
            'fiscal_position_id': self.fiscal_position_id.id,
            'account_analytic_id': self.account_analytic_id.id,
            'payment_term_id': self.payment_term_id.id,
            'grouped': self.grouped,
            'revision': self.revision,
            'sale_type_id': self.sale_type_id.id,
            'date_start': date_start,
            'date_end': date_end,
            'renewal': renewal,
            'use_index': self.use_index,
            'commentaires': self.commentaires,
            'of_mail_template_ids': [(6, 0, self.of_mail_template_ids.ids)],
        }

