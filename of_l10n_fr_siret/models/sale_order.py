# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def pdf_partner_siret_address_insert(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_partner_siret_address_insert')

    def pdf_partner_siret_customer_insert(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_partner_siret_customer_insert')
