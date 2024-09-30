# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pdf_address_title = fields.Boolean(string="Address title (Sale PDF display)", default=True)
    pdf_address_contact_titles = fields.Boolean(string="Titles (Sale PDF display)", default=True)
    pdf_address_contact_parent_name = fields.Boolean(string="Contact's parent name (Sale PDF display)", default=True)
    pdf_address_contact_name = fields.Boolean(string="Contact's name (Sale PDF display)", default=True)
    pdf_address_contact_phone = fields.Boolean(string="Phone (Sale PDF display)", default=True)
    pdf_address_contact_mobile = fields.Boolean(string="Mobile (Sale PDF display)", default=True)
    pdf_address_contact_fax = fields.Boolean(string="Fax (Sale PDF display)", default=True)
    pdf_address_contact_email = fields.Boolean(string="Email (Sale PDF Display)", default=True)
    pdf_invoicing_address_specific_title = fields.Boolean(string="Invoicing Address Specific Title (Sale PDF Display)")
    pdf_invoicing_address_specific_title_label = fields.Char(
        string="Invoicing Address Specific Title Label (Sale PDF Display)",
        size=30,
    )
    pdf_shipping_address_specific_title = fields.Boolean(string="Shipping Address Specific Title (Sale PDF Display)")
    pdf_shipping_address_specific_title_label = fields.Char(
        string="Shipping Address Specific Title Label (Sale PDF Display)", size=30
    )
    pdf_invoicing_shipping_address_specific_title = fields.Boolean(
        string="Invoicing and Shipping Address Specific Title (Sale PDF Display)"
    )
    pdf_invoicing_shipping_address_specific_title_label = fields.Char(
        string="Invoicing and Shipping Address Specific Title Label (Sale PDF Display)",
        size=30,
    )

    # Salesperson information
    pdf_salesperson_info = fields.Boolean(string="Salesperson Information (Sale PDF Display)", default=True)
    pdf_salesperson_name = fields.Boolean(string="Salesperson Name (Sale PDF Display)", default=True)
    pdf_salesperson_phone = fields.Boolean(string="Salesperson Phone (Sale PDF Display)", default=True)
    pdf_salesperson_mobile = fields.Boolean(string="Salesperson Mobile (Sale PDF Display)", default=True)
    pdf_salesperson_fax = fields.Boolean(string="Salesperson Fax (Sale PDF Display)", default=True)
    pdf_salesperson_email = fields.Boolean(string="Salesperson Email (Sale PDF Display)", default=True)

    # Customer information
    pdf_customer_info = fields.Boolean(string="Customer Information (Sale PDF Display)", default=True)
    pdf_customer_phone = fields.Boolean(string="Customer Phone (Sale PDF Display)", default=True)
    pdf_customer_mobile = fields.Boolean(string="Customer Mobile (Sale PDF Display)", default=True)
    pdf_customer_fax = fields.Boolean(string="Customer Fax (Sale PDF Display)", default=True)
    pdf_customer_email = fields.Boolean(string="Customer Email (Sale PDF Display)", default=True)

    # Other information
    pdf_payment_term_info = fields.Boolean(string="Payment terms (Sale PDF Display)", default=True)
    pdf_order_ref_info = fields.Boolean(string="Order reference (Sale PDF Display)", default=True)
    pdf_customer_ref_info = fields.Boolean(string="Customer reference (Sale PDF Display)", default=True)
    pdf_validity_info = fields.Boolean(string="Validity date (Sale PDF Display)", default=True)

    # Sections
    pdf_section_bg_color = fields.Char(
        string="Background color (Sale PDF Display)",
        help="Background color of the section headings. Default is white.",
        default="#FFFFFF",
    )
    pdf_section_font_color = fields.Char(
        string="Font color (Sale PDF Display)",
        help="Font color of the section headings. Default is black.",
        default="#000000",
    )

    # Order lines
    pdf_product_reference = fields.Boolean(string="Product reference (Sale PDF Display)")
    pdf_price_taxexcl = fields.Boolean(string="Price Tax Excl. (Sale PDF Display)")
    pdf_price_taxinc = fields.Boolean(string="Price Tax Incl. (Sale PDF Display)")
    pdf_print_image_level = fields.Selection(
        selection=[
            ("no", "Do not print"),
            ("line", "Print on each line"),
            ("appendix", "Print on appendix"),
            ("line_appendix", "Print first image on line and others on appendix"),
        ],
        string="Product images (Sale PDF Display)",
        default="no",
    )

    # Signatures insert
    pdf_signatures_insert = fields.Boolean(string="Signatures (Sale PDF Display)")
    pdf_customer_signature = fields.Boolean(string="Customer signature (Sale PDF Display)")
    pdf_vendor_signature = fields.Boolean(string="Salesman signature (Sale PDF Display)")

    pdf_signature_text = fields.Boolean(string="Signature statement (Sale PDF Display)")
    pdf_signature_text_label = fields.Char(string="Signature statement label (Sale PDF Display)")
