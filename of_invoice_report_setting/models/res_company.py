# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Address insert
    pdf_invoice_address_title = fields.Boolean(string="Address title (Invoice report settings)", default=True)
    pdf_invoice_address_contact_titles = fields.Boolean(string="Titles (Invoice report settings)")
    pdf_invoice_address_contact_parent_name = fields.Boolean(
        string="Contact's parent name  (Invoice report settings)", default=True
    )
    pdf_invoice_address_contact_name = fields.Boolean(string="Contact's name (Invoice report settings)", default=True)
    pdf_invoice_address_contact_phone = fields.Boolean(string="Phone (Invoice report settings)", default=True)
    pdf_invoice_address_contact_mobile = fields.Boolean(string="Mobile (Invoice report settings)", default=True)
    pdf_invoice_address_contact_fax = fields.Boolean(string="Fax (Invoice report settings)", default=True)
    pdf_invoice_address_contact_email = fields.Boolean(string="Email (Invoice report settings)", default=True)

    pdf_invoice_invoicing_address_specific_title = fields.Boolean(
        string="Invoicing Address Specific Title (Invoice report settings)"
    )
    pdf_invoice_invoicing_address_specific_title_label = fields.Char(
        string="Invoicing Address Specific Title Label (Invoice report settings)", size=30
    )
    pdf_invoice_shipping_address_specific_title = fields.Boolean(
        string="Shipping Address Specific Title (Invoice report settings)"
    )
    pdf_invoice_shipping_address_specific_title_label = fields.Char(
        string="Shipping Address Specific Title Label (Invoice report settings)", size=30
    )
    pdf_invoice_invoicing_shipping_address_specific_title = fields.Boolean(
        string="Invoicing and Shipping Address Specific Title (Invoice report settings)"
    )
    pdf_invoice_invoicing_shipping_address_specific_title_label = fields.Char(
        string="Invoicing and Shipping Address Specific Title Label (Invoice report settings)", size=30
    )

    # Salesperson information
    pdf_invoice_salesperson_info = fields.Boolean(
        string="Salesperson Information (Invoice report settings)", default=True
    )
    pdf_invoice_salesperson_name = fields.Boolean(string="Salesperson Name (Invoice report settings)", default=True)
    pdf_invoice_salesperson_phone = fields.Boolean(string="Salesperson Phone (Invoice report settings)", default=True)
    pdf_invoice_salesperson_mobile = fields.Boolean(string="Salesperson Mobile (Invoice report settings)", default=True)
    pdf_invoice_salesperson_fax = fields.Boolean(string="Salesperson Fax (Invoice report settings)", default=True)
    pdf_invoice_salesperson_email = fields.Boolean(string="Salesperson Email (Invoice report settings)", default=True)

    # Customer information
    pdf_invoice_customer_info = fields.Boolean(string="Customer Information (Invoice report settings)", default=True)
    pdf_invoice_customer_phone = fields.Boolean(string="Customer Phone (Invoice report settings)", default=True)
    pdf_invoice_customer_mobile = fields.Boolean(string="Customer Mobile (Invoice report settings)", default=True)
    pdf_invoice_customer_fax = fields.Boolean(string="Customer Fax (Invoice report settings)", default=True)
    pdf_invoice_customer_email = fields.Boolean(string="Customer Email (Invoice report settings)", default=True)

    # Other information
    pdf_invoice_legal_notice = fields.Text(string="Legal notice (Invoice report settings)")
    pdf_invoice_payment_term_info = fields.Boolean(string="Payment term info (Invoice report settings)")
    pdf_invoice_customer_ref_info = fields.Boolean(string="Customer ref info (Invoice report settings)")

    # Sections
    pdf_invoice_section_bg_color = fields.Char(
        string="Background color (Invoice report settings)",
        help="Background color of the section headings. Default is white.",
        default="#FFFFFF",
    )
    pdf_invoice_section_font_color = fields.Char(
        string="Font color (Invoice report settings)",
        help="Font color of the section headings. Default is black.",
        default="#000000",
    )

    # Invoice lines
    pdf_invoice_product_reference = fields.Boolean(string="Product reference (Invoice report settings)", default=True)
    pdf_invoice_price_taxexcl = fields.Boolean(
        string="Price Tax Excl. (Invoice report settings)",
        readonly=False,
        help="Display price without tax on invoice report",
    )
    pdf_invoice_price_taxinc = fields.Boolean(
        string="Price Tax Incl. (Invoice report settings)",
        readonly=False,
        help="Display price with tax on invoice report",
    )
