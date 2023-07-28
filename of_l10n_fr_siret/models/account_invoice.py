# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def pdf_partner_siret_display(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_partner_siret_display') or 0
