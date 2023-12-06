# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

SELECTION_PRINT_IMAGE_LEVEL = [
    ('no', "Do not print"),
    ('line', "Print on each line"),
    ('appendix', "Print on appendix"),
    ('line_appendix', "Print first image on line and others on appendix"),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    pdf_address_title = fields.Boolean(string="Address title", default=True)
    pdf_address_contact_titles = fields.Boolean(string="Titles", default=True)
    pdf_address_contact_parent_name = fields.Boolean(string="Contact's parent name", default=True)
    pdf_address_contact_name = fields.Boolean(string="Contact's name", default=True)
    pdf_address_contact_phone = fields.Boolean(string="Phone", default=True)
    pdf_address_contact_mobile = fields.Boolean(string="Mobile", default=True)
    pdf_address_contact_fax = fields.Boolean(string="Fax", default=True)
    pdf_address_contact_email = fields.Boolean(string="Email", default=True)
    pdf_invoicing_address_specific_title = fields.Boolean(string="Invoicing Address Specific Title")
    pdf_invoicing_address_specific_title_label = fields.Char(
        string="Invoicing Address Specific Title Label",
        size=30,
    )
    pdf_shipping_address_specific_title = fields.Boolean(string="Shipping Address Specific Title")
    pdf_shipping_address_specific_title_label = fields.Char(string="Shipping Address Specific Title Label", size=30)
    pdf_invoicing_shipping_address_specific_title = fields.Boolean(
        string="Invoicing and Shipping Address Specific Title"
    )
    pdf_invoicing_shipping_address_specific_title_label = fields.Char(
        string="Invoicing and Shipping Address Specific Title Label",
        size=30,
    )

    # Salesperson information
    pdf_salesperson_info = fields.Boolean(string="Salesperson Information", default=True)
    pdf_salesperson_name = fields.Boolean(string="Salesperson Name", default=True)
    pdf_salesperson_phone = fields.Boolean(string="Salesperson Phone", default=True)
    pdf_salesperson_mobile = fields.Boolean(string="Salesperson Mobile", default=True)
    pdf_salesperson_fax = fields.Boolean(string="Salesperson Fax", default=True)
    pdf_salesperson_email = fields.Boolean(string="Salesperson Email", default=True)

    # Customer information
    pdf_customer_info = fields.Boolean(string="Customer Information", default=True)
    pdf_customer_phone = fields.Boolean(string="Customer Phone", default=True)
    pdf_customer_mobile = fields.Boolean(string="Customer Mobile", default=True)
    pdf_customer_fax = fields.Boolean(string="Customer Fax", default=True)
    pdf_customer_email = fields.Boolean(string="Customer Email", default=True)

    # Other information
    pdf_payment_term_info = fields.Boolean(string="Payment terms", default=True)
    pdf_order_ref_info = fields.Boolean(string="Order reference", default=True)
    pdf_customer_ref_info = fields.Boolean(string="Customer reference", default=True)
    pdf_validity_info = fields.Boolean(string="Validity date", default=True)

    # Sections
    pdf_section_bg_color = fields.Char(
        string="Background color", help="Background color of the section headings. Default is white.", default="#FFFFFF"
    )
    pdf_section_font_color = fields.Char(
        string="Font color", help="Font color of the section headings. Default is black.", default="#000000"
    )

    # Order lines
    pdf_product_reference = fields.Boolean(string="Product reference")
    pdf_price_taxexcl = fields.Boolean(string="Price Tax Excl.")
    pdf_price_taxinc = fields.Boolean(string="Price Tax Incl.")
    pdf_print_image_level = fields.Selection(
        selection=SELECTION_PRINT_IMAGE_LEVEL,
        string="Product images",
        default='no',
    )

    # Signatures insert
    pdf_signatures_insert = fields.Boolean(string="Signatures")
    pdf_customer_signature = fields.Boolean(string="Customer signature")
    pdf_vendor_signature = fields.Boolean(string="Salesman signature")

    pdf_signature_text = fields.Boolean(string="Signature statement")
    pdf_signature_text_label = fields.Char(string="Signature statement label")
