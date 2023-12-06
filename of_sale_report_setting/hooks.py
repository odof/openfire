# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import SUPERUSER_ID, api


def _update_all_company(env):
    company_ids = env['res.company'].search([])
    value = {
        'pdf_address_title': True,
        'pdf_address_contact_titles': True,
        'pdf_address_contact_parent_name': True,
        'pdf_address_contact_name': True,
        'pdf_address_contact_phone': True,
        'pdf_address_contact_mobile': True,
        'pdf_address_contact_fax': True,
        'pdf_address_contact_email': True,
        'pdf_salesperson_info': True,
        'pdf_salesperson_name': True,
        'pdf_salesperson_phone': True,
        'pdf_salesperson_mobile': True,
        'pdf_salesperson_fax': True,
        'pdf_salesperson_email': True,
        'pdf_customer_info': True,
        'pdf_customer_phone': True,
        'pdf_customer_mobile': True,
        'pdf_customer_fax': True,
        'pdf_customer_email': True,
        'pdf_payment_term_info': True,
        'pdf_order_ref_info': True,
        'pdf_customer_ref_info': True,
        'pdf_validity_info': True,
        'pdf_section_bg_color': "#FFFFFF",
        'pdf_section_font_color': "#000000",
        'pdf_product_reference': True,
        'pdf_price_taxexcl': True,
        'pdf_price_taxinc': True,
        'pdf_print_image_level': "no",
        'pdf_signatures_insert': True,
        'pdf_customer_signature': True,
        'pdf_vendor_signature': True,
    }
    company_ids.write(value)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_all_company(env)
