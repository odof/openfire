# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSaleDocumentLayout(models.TransientModel):
    """
    Transient model to configure the layout of the sale document in a specific wizard that is not `res.config.settings`.
    It mimics `res.config.settings`.
    """

    _name = "of.sale.document.layout"
    _inherit = "of.base.document.layout"
    _description = "Sale Document Layout"

    company_id = fields.Many2one(comodel_name="res.company", default=lambda self: self.env.company, required=True)

    # Address insert
    pdf_address_title = fields.Boolean(string="Address title", related="company_id.pdf_address_title", readonly=False)
    pdf_address_contact_titles = fields.Boolean(
        string="Titles", related="company_id.pdf_address_contact_titles", readonly=False
    )
    pdf_address_contact_parent_name = fields.Boolean(
        string="Contact's parent name", related="company_id.pdf_address_contact_parent_name", readonly=False
    )
    pdf_address_contact_name = fields.Boolean(
        string="Contact's name", related="company_id.pdf_address_contact_name", readonly=False
    )
    pdf_address_contact_phone = fields.Boolean(
        string="Phone", related="company_id.pdf_address_contact_phone", readonly=False
    )
    pdf_address_contact_mobile = fields.Boolean(
        string="Mobile", related="company_id.pdf_address_contact_mobile", readonly=False
    )
    pdf_address_contact_fax = fields.Boolean(string="Fax", related="company_id.pdf_address_contact_fax", readonly=False)
    pdf_address_contact_email = fields.Boolean(
        string="Email", related="company_id.pdf_address_contact_email", readonly=False
    )
    pdf_invoicing_address_specific_title = fields.Boolean(
        string="Invoicing Address Specific Title",
        related="company_id.pdf_invoicing_address_specific_title",
        readonly=False,
    )
    pdf_invoicing_address_specific_title_label = fields.Char(
        string="Invoicing Address Specific Title Label",
        size=30,
        related="company_id.pdf_invoicing_address_specific_title_label",
        readonly=False,
    )
    pdf_shipping_address_specific_title = fields.Boolean(
        string="Shipping Address Specific Title",
        related="company_id.pdf_shipping_address_specific_title",
        readonly=False,
    )
    pdf_shipping_address_specific_title_label = fields.Char(
        string="Shipping Address Specific Title Label",
        size=30,
        related="company_id.pdf_shipping_address_specific_title_label",
        readonly=False,
    )
    pdf_invoicing_shipping_address_specific_title = fields.Boolean(
        string="Invoicing and Shipping Address Specific Title",
        related="company_id.pdf_invoicing_shipping_address_specific_title",
        readonly=False,
    )
    pdf_invoicing_shipping_address_specific_title_label = fields.Char(
        string="Invoicing and Shipping Address Specific Title Label",
        size=30,
        related="company_id.pdf_invoicing_shipping_address_specific_title_label",
        readonly=False,
    )

    # Salesperson information
    pdf_salesperson_info = fields.Boolean(
        string="Salesperson Information", related="company_id.pdf_salesperson_info", readonly=False
    )
    pdf_salesperson_name = fields.Boolean(
        string="Salesperson Name", related="company_id.pdf_salesperson_name", readonly=False
    )
    pdf_salesperson_phone = fields.Boolean(
        string="Salesperson Phone", related="company_id.pdf_salesperson_phone", readonly=False
    )
    pdf_salesperson_mobile = fields.Boolean(
        string="Salesperson Mobile", related="company_id.pdf_salesperson_mobile", readonly=False
    )
    pdf_salesperson_fax = fields.Boolean(
        string="Salesperson Fax", related="company_id.pdf_salesperson_fax", readonly=False
    )
    pdf_salesperson_email = fields.Boolean(
        string="Salesperson Email", related="company_id.pdf_salesperson_email", readonly=False
    )

    # Customer information
    pdf_customer_info = fields.Boolean(
        string="Customer Information", related="company_id.pdf_customer_info", readonly=False
    )
    pdf_customer_phone = fields.Boolean(
        string="Customer Phone", related="company_id.pdf_customer_phone", readonly=False
    )
    pdf_customer_mobile = fields.Boolean(
        string="Customer Mobile", related="company_id.pdf_customer_mobile", readonly=False
    )
    pdf_customer_fax = fields.Boolean(string="Customer Fax", related="company_id.pdf_customer_fax", readonly=False)
    pdf_customer_email = fields.Boolean(
        string="Customer Email", related="company_id.pdf_customer_email", readonly=False
    )

    # Other information
    pdf_payment_term_info = fields.Boolean(
        string="Payment terms", related="company_id.pdf_payment_term_info", readonly=False
    )
    pdf_order_ref_info = fields.Boolean(
        string="Order reference", related="company_id.pdf_order_ref_info", readonly=False
    )
    pdf_customer_ref_info = fields.Boolean(
        string="Customer reference", related="company_id.pdf_customer_ref_info", readonly=False
    )
    pdf_validity_info = fields.Boolean(string="Validity date", related="company_id.pdf_validity_info", readonly=False)

    # Sections
    pdf_section_bg_color = fields.Char(
        string="Background color",
        related="company_id.pdf_section_bg_color",
        help="Background color of the section headings. Default is white.",
        readonly=False,
    )
    pdf_section_font_color = fields.Char(
        string="Font color",
        related="company_id.pdf_section_font_color",
        help="Font color of the section headings. Default is black.",
        readonly=False,
    )

    # Order lines
    pdf_product_reference = fields.Boolean(
        string="Product reference", related="company_id.pdf_product_reference", readonly=False
    )
    pdf_price_taxexcl = fields.Boolean(string="Price Tax Excl.", related="company_id.pdf_price_taxexcl", readonly=False)
    pdf_price_taxinc = fields.Boolean(string="Price Tax Incl.", related="company_id.pdf_price_taxinc", readonly=False)
    pdf_print_image_level = fields.Selection(
        string="Product images",
        related="company_id.pdf_print_image_level",  # FIXME: should not be related, that's a module install
        readonly=False,
    )
    module_of_sale_report_setting_product_multi_image = fields.Boolean(
        compute="_compute_module_of_sale_report_setting_product_multi_image", store=True, readonly=False
    )

    group_of_sale_report_print_attachment = fields.Boolean(
        string="Product attachments", implied_group="of_sale_report_setting.group_of_sale_report_print_attachment"
    )

    # Signatures insert
    pdf_signatures_insert = fields.Boolean(
        string="Signatures", related="company_id.pdf_signatures_insert", readonly=False
    )
    pdf_customer_signature = fields.Boolean(
        string="Customer signature", related="company_id.pdf_customer_signature", readonly=False
    )
    pdf_vendor_signature = fields.Boolean(
        string="Salesman signature", related="company_id.pdf_vendor_signature", readonly=False
    )
    group_pdf_prefill_vendor_signature = fields.Boolean(
        string="Pre-filled salesman signature",
        implied_group="of_sale_report_setting.group_of_pdf_prefill_vendor_signature",
    )
    pdf_signature_text = fields.Boolean(
        string="Signature statement", related="company_id.pdf_signature_text", readonly=False
    )
    pdf_signature_text_label = fields.Char(
        string="Signature statement label", related="company_id.pdf_signature_text_label", readonly=False
    )

    # ---------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------

    @api.depends("pdf_print_image_level")
    def _compute_module_of_sale_report_setting_product_multi_image(self):
        for wizard in self:
            if wizard.pdf_print_image_level in ["appendix", "line_appendix"]:
                wizard.module_of_sale_report_setting_product_multi_image = True

    # ---------------------------------------------------------
    # Onchange methods
    # ---------------------------------------------------------

    @api.onchange("pdf_salesperson_info")
    def onchange_pdf_salesperson_info(self):
        # we need to check if the value has changed because the onchange is called when the form is loaded
        has_changed = self.company_id.pdf_salesperson_info != self.pdf_salesperson_info
        if has_changed and self.pdf_salesperson_info and not self.pdf_salesperson_name:
            self.pdf_salesperson_name = True

    @api.onchange("pdf_signatures_insert")
    def _onchange_pdf_signatures_insert(self):
        # we need to check if the value has changed because the onchange is called when the form is loaded
        has_changed = self.company_id.pdf_signatures_insert != self.pdf_signatures_insert
        if has_changed and self.pdf_signatures_insert and not self.pdf_customer_signature:
            self.pdf_customer_signature = True
        if has_changed and self.pdf_signatures_insert and not self.pdf_vendor_signature:
            self.pdf_vendor_signature = True

    @api.onchange("pdf_vendor_signature")
    def _onchange_pdf_vendor_signature(self):
        if not self.pdf_vendor_signature:
            self.group_pdf_prefill_vendor_signature = False
