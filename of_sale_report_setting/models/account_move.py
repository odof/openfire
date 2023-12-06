# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ---------------------------------------------------------
    # Helper methods for QWeb reports
    # ---------------------------------------------------------

    def pdf_address_title(self):
        """Same as sale_order.py"""
        return self.company_id.pdf_address_title

    def pdf_invoicing_address_specific_title(self):
        """Same as sale_order.py"""
        return self.company_id.pdf_invoicing_address_specific_title

    def pdf_invoicing_address_specific_title_label(self):
        """Same as sale_order.py"""
        return self.company_id.pdf_invoicing_address_specific_title_label

    def pdf_shipping_address_specific_title(self):
        """Same as sale_order.py"""
        return self.company_id.pdf_shipping_address_specific_title

    def pdf_shipping_address_specific_title_label(self):
        """Same as sale_order.py"""
        return self.company_id.pdf_shipping_address_specific_title_label

    def pdf_invoicing_shipping_address_specific_title(self):
        """Same as sale_order.py"""
        return self.company_id.pdf_invoicing_shipping_address_specific_title

    def pdf_invoicing_shipping_address_specific_title_label(self):
        """Same as sale_order.py"""
        return self.company_id.pdf_invoicing_shipping_address_specific_title_label
