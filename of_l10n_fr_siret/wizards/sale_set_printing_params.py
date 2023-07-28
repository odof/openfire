# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OFSaleWizardSetPrintingParams(models.TransientModel):
    _inherit = 'of.sale.wizard.set.printing.params'

    # Address insert
    pdf_partner_siret_address_insert = fields.Boolean(
        string="SIRET", default=False, help="If checked, displays the customer's SIRET in the address insert")

    # Customers insert
    pdf_partner_siret_customer_insert = fields.Boolean(
        string="SIRET", default=False, help="If checked, displays the customer's SIRET in the customer insert")

    def set_pdf_partner_siret_address_insert(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_partner_siret_address_insert', self.pdf_partner_siret_address_insert)

    def set_pdf_partner_siret_customer_insert(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_partner_siret_customer_insert', self.pdf_partner_siret_customer_insert)
