# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoiceSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    pdf_partner_siret_display = fields.Selection(
        selection=[
            (1, "Display in main address box"),
            (2, "Display in additional information insert"),
            (3, "Display in main address insert and in additional information insert")
        ], string="(OF) SIRET",
        help="Where to display the SIRET in PDF reports? Leave blank to avoid display.")

    @api.multi
    def set_pdf_partner_siret_display(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_partner_siret_display', self.pdf_partner_siret_display)
