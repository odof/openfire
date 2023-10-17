# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    of_display_name = fields.Text(string="Display name for reports", compute='_compute_of_display_name')

    def _compute_of_display_name(self):
        """Compute the display name for the invoice report"""
        display_ref = self.company_id.pdf_invoice_product_reference
        for line in self:
            if display_ref:
                line.of_display_name = line.name
            else:
                name = line.with_context(lang=line.move_id.partner_id.lang, partner=line.move_id.partner_id.id).name
                if match := re.search(r'\[(.*?)\]', name):
                    name = name.replace(match[0], '').strip()
                line.of_display_name = name
