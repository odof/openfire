# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _update_all_company(env):
    company_ids = env["res.company"].search([])
    fr_companies = company_ids.filtered(lambda c: c.country_id.code == "FR")
    other_companies = company_ids - fr_companies

    value = {
        'pdf_invoice_address_title': True,
        'pdf_invoice_address_contact_parent_name': True,
        'pdf_invoice_address_contact_name': True,
        'pdf_invoice_address_contact_phone': True,
        'pdf_invoice_address_contact_mobile': True,
        'pdf_invoice_address_contact_fax': True,
        'pdf_invoice_address_contact_email': True,
        'pdf_invoice_invoicing_address_specific_title': False,
        'pdf_invoice_shipping_address_specific_title_label': "Shipping Address:",
        'pdf_invoice_salesperson_info': True,
        'pdf_invoice_salesperson_name': True,
        'pdf_invoice_salesperson_phone': True,
        'pdf_invoice_salesperson_mobile': True,
        'pdf_invoice_salesperson_fax': True,
        'pdf_invoice_salesperson_email': True,
        'pdf_invoice_customer_info': True,
        'pdf_invoice_customer_phone': True,
        'pdf_invoice_customer_mobile': True,
        'pdf_invoice_customer_fax': True,
        'pdf_invoice_customer_email': True,
        'pdf_invoice_section_bg_color': "#FFFFFF",
        'pdf_invoice_section_font_color': "#000000",
        'pdf_invoice_product_reference': True,
        'pdf_invoice_price_taxexcl': True,
        'pdf_invoice_price_taxinc': True,
    }
    fr_companies.write(value | {"pdf_invoice_shipping_address_specific_title_label": "Adresse de livraison :"})
    other_companies.write(value)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_all_company(env)
