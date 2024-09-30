# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ---------------------------------------------------------
    # Helper methods for QWeb reports
    # ---------------------------------------------------------

    def pdf_address_title(self):
        return self.company_id.pdf_address_title

    def pdf_address_contact_titles(self):
        return self.company_id.pdf_address_contact_titles

    def pdf_address_contact_parent_name(self):
        return self.company_id.pdf_address_contact_parent_name

    def pdf_address_contact_name(self):
        return self.company_id.pdf_address_contact_name

    def pdf_address_contact_phone(self):
        return self.company_id.pdf_address_contact_phone

    def pdf_address_contact_mobile(self):
        return self.company_id.pdf_address_contact_mobile

    def pdf_address_contact_fax(self):
        return self.company_id.pdf_address_contact_fax

    def pdf_address_contact_email(self):
        return self.company_id.pdf_address_contact_email

    def pdf_invoicing_address_specific_title(self):
        return self.company_id.pdf_invoicing_address_specific_title

    def pdf_invoicing_address_specific_title_label(self):
        return self.company_id.pdf_invoicing_address_specific_title_label

    def pdf_shipping_address_specific_title(self):
        return self.company_id.pdf_shipping_address_specific_title

    def pdf_shipping_address_specific_title_label(self):
        return self.company_id.pdf_shipping_address_specific_title_label

    def pdf_invoicing_shipping_address_specific_title(self):
        return self.company_id.pdf_invoicing_shipping_address_specific_title

    def pdf_invoicing_shipping_address_specific_title_label(self):
        return self.company_id.pdf_invoicing_shipping_address_specific_title_label

    def pdf_salesperson_info(self):
        return self.company_id.pdf_salesperson_info

    def pdf_salesperson_name(self):
        return self.company_id.pdf_salesperson_name

    def pdf_salesperson_phone(self):
        return self.company_id.pdf_salesperson_phone

    def pdf_salesperson_mobile(self):
        return self.company_id.pdf_salesperson_mobile

    def pdf_salesperson_fax(self):
        return self.company_id.pdf_salesperson_fax

    def pdf_salesperson_email(self):
        return self.company_id.pdf_salesperson_email

    def pdf_customer_info(self):
        return self.company_id.pdf_customer_info

    def pdf_customer_phone(self):
        return self.company_id.pdf_customer_phone

    def pdf_customer_mobile(self):
        return self.company_id.pdf_customer_mobile

    def pdf_customer_fax(self):
        return self.company_id.pdf_customer_fax

    def pdf_customer_email(self):
        return self.company_id.pdf_customer_email

    def pdf_payment_term_info(self):
        return self.company_id.pdf_payment_term_info

    def pdf_order_ref_info(self):
        return self.company_id.pdf_order_ref_info

    def pdf_customer_ref_info(self):
        return self.company_id.pdf_customer_ref_info

    def pdf_validity_info(self):
        return self.company_id.pdf_validity_info

    def get_color_section(self):
        return self.company_id.pdf_section_bg_color or "#FFFFFF"

    def get_color_font(self):
        return self.company_id.pdf_section_font_color or "#000000"

    def pdf_price_taxexcl(self):
        return self.company_id.pdf_price_taxexcl

    def pdf_price_taxinc(self):
        return self.company_id.pdf_price_taxinc

    def pdf_print_image_level(self):
        return self.company_id.pdf_print_image_level

    def pdf_signatures_insert(self):
        return self.company_id.pdf_signatures_insert

    def pdf_customer_signature(self):
        return self.company_id.pdf_customer_signature

    def pdf_vendor_signature(self):
        return self.company_id.pdf_vendor_signature

    def pdf_prefill_vendor_signature(self):
        return self.env.user.has_group("of_sale_report_setting.group_of_pdf_prefill_vendor_signature")

    def pdf_signature_text(self):
        return self.company_id.pdf_signature_text

    def pdf_signature_text_label(self):
        return self.company_id.pdf_signature_text_label

    def pdf_product_reference(self):
        return self.company_id.pdf_product_reference
