# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFInvoiceDocumentLayout(models.TransientModel):
    """
    Transient model to configure the layout of the invoice document in a specific wizard that is not
    `res.config.settings`.
    It mimics `res.config.settings`.
    """

    _name = 'of.invoice.document.layout'
    _inherit = 'of.base.document.layout'
    _description = "Printing Settings for Invoice"

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company, required=True)

    # Address insert
    pdf_invoice_address_title = fields.Boolean(
        related="company_id.pdf_invoice_address_title", readonly=False, string="Address title"
    )
    pdf_invoice_address_contact_titles = fields.Boolean(
        related="company_id.pdf_invoice_address_contact_titles", readonly=False, string="Titles"
    )
    pdf_invoice_address_contact_parent_name = fields.Boolean(
        related="company_id.pdf_invoice_address_contact_parent_name", readonly=False, string="Parent name"
    )
    pdf_invoice_address_contact_name = fields.Boolean(
        related="company_id.pdf_invoice_address_contact_name", readonly=False, string="Name"
    )
    pdf_invoice_address_contact_phone = fields.Boolean(
        related="company_id.pdf_invoice_address_contact_phone", readonly=False, string="Phone"
    )
    pdf_invoice_address_contact_mobile = fields.Boolean(
        related="company_id.pdf_invoice_address_contact_mobile", readonly=False, string="Mobile"
    )
    pdf_invoice_address_contact_fax = fields.Boolean(
        related="company_id.pdf_invoice_address_contact_fax", readonly=False, string="Fax"
    )
    pdf_invoice_address_contact_email = fields.Boolean(
        related="company_id.pdf_invoice_address_contact_email", readonly=False, string="Email"
    )
    pdf_invoice_invoicing_address_specific_title = fields.Boolean(
        string="Invoicing Address Specific Title",
        related='company_id.pdf_invoice_invoicing_address_specific_title',
        readonly=False,
    )
    pdf_invoice_invoicing_address_specific_title_label = fields.Char(
        string="Invoicing Address Specific Title Label",
        size=30,
        related='company_id.pdf_invoice_invoicing_address_specific_title_label',
        readonly=False,
    )
    pdf_invoice_shipping_address_specific_title = fields.Boolean(
        string="Shipping Address Specific Title",
        related='company_id.pdf_invoice_shipping_address_specific_title',
        readonly=False,
    )
    pdf_invoice_shipping_address_specific_title_label = fields.Char(
        string="Shipping Address Specific Title Label",
        size=30,
        related='company_id.pdf_invoice_shipping_address_specific_title_label',
        readonly=False,
    )
    pdf_invoice_invoicing_shipping_address_specific_title = fields.Boolean(
        string="Invoicing and Shipping Address Specific Title",
        related='company_id.pdf_invoice_invoicing_shipping_address_specific_title',
        readonly=False,
    )
    pdf_invoice_invoicing_shipping_address_specific_title_label = fields.Char(
        string="Invoicing and Shipping Address Specific Title Label",
        size=30,
        related='company_id.pdf_invoice_invoicing_shipping_address_specific_title_label',
        readonly=False,
    )

    # Salesperson information
    pdf_invoice_salesperson_info = fields.Boolean(
        related="company_id.pdf_invoice_salesperson_info", readonly=False, string="Salesperson Information"
    )
    pdf_invoice_salesperson_name = fields.Boolean(
        related="company_id.pdf_invoice_salesperson_name", readonly=False, string="Name"
    )
    pdf_invoice_salesperson_phone = fields.Boolean(
        related="company_id.pdf_invoice_salesperson_phone", readonly=False, string="Phone"
    )
    pdf_invoice_salesperson_mobile = fields.Boolean(
        related="company_id.pdf_invoice_salesperson_mobile", readonly=False, string="Mobile"
    )
    pdf_invoice_salesperson_fax = fields.Boolean(
        related="company_id.pdf_invoice_salesperson_fax", readonly=False, string="Fax"
    )
    pdf_invoice_salesperson_email = fields.Boolean(
        related="company_id.pdf_invoice_salesperson_email", readonly=False, string="Email"
    )

    # Customer information
    pdf_invoice_customer_info = fields.Boolean(
        related="company_id.pdf_invoice_customer_info", readonly=False, string="Customer Information"
    )
    pdf_invoice_customer_phone = fields.Boolean(
        related="company_id.pdf_invoice_customer_phone", readonly=False, string="Phone"
    )
    pdf_invoice_customer_mobile = fields.Boolean(
        related="company_id.pdf_invoice_customer_mobile", readonly=False, string="Mobile"
    )
    pdf_invoice_customer_fax = fields.Boolean(
        related="company_id.pdf_invoice_customer_fax", readonly=False, string="Fax"
    )
    pdf_invoice_customer_email = fields.Boolean(
        related="company_id.pdf_invoice_customer_email", readonly=False, string="Email"
    )

    # Other information
    pdf_invoice_legal_notice = fields.Text(
        related="company_id.pdf_invoice_legal_notice", readonly=False, string="Legal notice"
    )
    pdf_invoice_payment_term_info = fields.Boolean(
        related="company_id.pdf_invoice_payment_term_info", readonly=False, string="Payment term info"
    )
    pdf_invoice_customer_ref_info = fields.Boolean(
        related="company_id.pdf_invoice_customer_ref_info", readonly=False, string="Customer ref info"
    )

    # Sections
    pdf_invoice_section_bg_color = fields.Char(
        related="company_id.pdf_invoice_section_bg_color",
        readonly=False,
        string="Background color",
        help="Background color of the section headings. Default is white.",
    )
    pdf_invoice_section_font_color = fields.Char(
        related="company_id.pdf_invoice_section_font_color",
        readonly=False,
        string="Font color",
        help="Font color of the section headings. Default is black.",
    )

    # Invoice lines
    pdf_invoice_product_reference = fields.Boolean(
        related="company_id.pdf_invoice_product_reference", readonly=False, string="Product reference"
    )
    pdf_invoice_price_taxexcl = fields.Boolean(
        string="Price Tax Excl.", related='company_id.pdf_invoice_price_taxexcl', readonly=False
    )
    pdf_invoice_price_taxinc = fields.Boolean(
        string="Price Tax Incl.", related='company_id.pdf_invoice_price_taxinc', readonly=False
    )

    # Summary invoice amounts
    module_of_account_sale_report_totals = fields.Boolean(string="Invoice totals management")

    # ---------------------------------------------------------
    # Onchange methods
    # ---------------------------------------------------------

    @api.onchange('pdf_invoice_salesperson_info')
    def onchange_pdf_invoice_salesperson_info(self):
        # we need to check if the value has changed because the onchange is called when the form is loaded
        has_changed = self.company_id.pdf_invoice_salesperson_info != self.pdf_invoice_salesperson_info
        if has_changed and self.pdf_invoice_salesperson_info and not self.pdf_invoice_salesperson_name:
            self.pdf_invoice_salesperson_name = True
