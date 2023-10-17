# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ---------------------------------------------------------
    # Helper methods for QWeb reports
    # ---------------------------------------------------------

    def pdf_invoice_address_title(self):
        """Get the title for the address section in the PDF invoice."""
        return self.company_id.pdf_invoice_address_title

    def pdf_invoice_invoicing_address_title(self):
        """Get the title for the invoicing address section in the PDF invoice."""
        return self.company_id.pdf_invoice_invoicing_address_specific_title

    def pdf_invoice_invoicing_address_title_label(self):
        """Get the label for the invoicing address title in the PDF invoice."""
        return self.company_id.pdf_invoice_invoicing_address_specific_title_label

    def pdf_invoice_shipping_address_title(self):
        """Get the title for the shipping address section in the PDF invoice."""
        return self.company_id.pdf_invoice_shipping_address_specific_title

    def pdf_invoice_shipping_address_title_label(self):
        """Get the label for the shipping address title in the PDF invoice."""
        return self.company_id.pdf_invoice_shipping_address_specific_title_label

    def pdf_invoice_invoicing_shipping_address_title(self):
        """Get the title for the invoicing and shipping address section in the PDF invoice."""
        return self.company_id.pdf_invoice_invoicing_shipping_address_specific_title

    def pdf_invoice_invoicing_shipping_address_title_label(self):
        """Get the label for the invoicing and shipping address title in the PDF invoice."""
        return self.company_id.pdf_invoice_invoicing_shipping_address_specific_title_label

    def pdf_invoice_address_contact_parent_name(self):
        """Get the parent name for the contact in the PDF invoice address section."""
        return self.company_id.pdf_invoice_address_contact_parent_name

    def pdf_invoice_address_contact_name(self):
        """Get the name for the contact in the PDF invoice address section."""
        return self.company_id.pdf_invoice_address_contact_name

    def pdf_invoice_address_contact_titles(self):
        """Get the titles for the contact in the PDF invoice address section."""
        return self.company_id.pdf_invoice_address_contact_titles

    def pdf_invoice_address_phone(self):
        """Get the phone number for the contact in the PDF invoice address section."""
        return self.company_id.pdf_invoice_address_contact_phone

    def pdf_invoice_address_mobile(self):
        """Get the mobile number for the contact in the PDF invoice address section."""
        return self.company_id.pdf_invoice_address_contact_mobile

    def pdf_invoice_address_fax(self):
        """Get the fax number for the contact in the PDF invoice address section."""
        return self.company_id.pdf_invoice_address_contact_fax

    def pdf_invoice_address_email(self):
        """Get the email address for the contact in the PDF invoice address section."""
        return self.company_id.pdf_invoice_address_contact_email

    def pdf_invoice_salesperson_name(self):
        """Get the name of the salesperson in the PDF invoice."""
        return self.company_id.pdf_invoice_salesperson_name

    def pdf_invoice_salesperson_phone(self):
        """Get the phone number of the salesperson in the PDF invoice."""
        return self.company_id.pdf_invoice_salesperson_phone

    def pdf_invoice_salesperson_mobile(self):
        """Get the mobile number of the salesperson in the PDF invoice."""
        return self.company_id.pdf_invoice_salesperson_mobile

    def pdf_invoice_salesperson_fax(self):
        """Get the fax number of the salesperson in the PDF invoice."""
        return self.company_id.pdf_invoice_salesperson_fax

    def pdf_invoice_salesperson_email(self):
        """Get the email address of the salesperson in the PDF invoice."""
        return self.company_id.pdf_invoice_salesperson_email

    def pdf_invoice_salesperson_info(self):
        """Get the additional information about the salesperson in the PDF invoice."""
        return self.company_id.pdf_invoice_salesperson_info

    def pdf_invoice_customer_phone(self):
        """Get the phone number of the customer in the PDF invoice."""
        return self.company_id.pdf_invoice_customer_phone

    def pdf_invoice_customer_mobile(self):
        """Get the mobile number of the customer in the PDF invoice."""
        return self.company_id.pdf_invoice_customer_mobile

    def pdf_invoice_customer_fax(self):
        """Get the fax number of the customer in the PDF invoice."""
        return self.company_id.pdf_invoice_customer_fax

    def pdf_invoice_customer_email(self):
        """Get the email address of the customer in the PDF invoice."""
        return self.company_id.pdf_invoice_customer_email

    def pdf_invoice_customer_info(self):
        """Get additional information about the customer in the PDF invoice."""
        return self.company_id.pdf_invoice_customer_info

    def pdf_invoice_legal_notice(self):
        """Get the legal notice for the PDF invoice."""
        return self.company_id.pdf_invoice_legal_notice

    def pdf_invoice_invoice_payment_term_info(self):
        """Get the payment term information for the PDF invoice."""
        return self.company_id.pdf_invoice_payment_term_info

    def pdf_invoice_invoice_customer_ref_info(self):
        """Get the customer reference information for the PDF invoice."""
        return self.company_id.pdf_invoice_customer_ref_info

    def pdf_invoice_invoice_price_taxexcl(self):
        """Get the price excluding tax for the PDF invoice."""
        return self.company_id.pdf_invoice_price_taxexcl

    def pdf_invoice_invoice_price_taxinc(self):
        """Get the price including tax for the PDF invoice."""
        return self.company_id.pdf_invoice_price_taxinc

    def pdf_invoice_get_color_section(self):
        """Get the color of the section background for the PDF invoice."""
        return self.env.company.pdf_invoice_section_bg_color

    def pdf_invoice_get_color_font(self):
        """Get the color of the section font for the PDF invoice."""
        return self.env.company.pdf_invoice_section_font_color
