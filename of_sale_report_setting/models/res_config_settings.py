# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Address insert
    pdf_address_title = fields.Boolean(
        string="Address title", config_parameter='of.sale.report.setting.pdf_address_title'
    )
    pdf_address_contact_titles = fields.Boolean(
        string="Titles", config_parameter='of.sale.report.setting.pdf_address_contact_titles'
    )
    pdf_address_contact_parent_name = fields.Boolean(
        string="Contact's parent name", config_parameter='of.sale.report.setting.pdf_address_contact_parent_name'
    )
    pdf_address_contact_name = fields.Boolean(
        string="Contact's name", config_parameter='of.sale.report.setting.pdf_address_contact_name'
    )
    pdf_address_contact_phone = fields.Boolean(
        string="Phone", config_parameter='of.sale.report.setting.pdf_address_contact_phone'
    )
    pdf_address_contact_mobile = fields.Boolean(
        string="Mobile", config_parameter='of.sale.report.setting.pdf_address_contact_mobile'
    )
    pdf_address_contact_fax = fields.Boolean(
        string="Fax", config_parameter='of.sale.report.setting.pdf_address_contact_fax'
    )
    pdf_address_contact_email = fields.Boolean(
        string="Email", config_parameter='of.sale.report.setting.pdf_address_contact_email'
    )
    pdf_invoicing_address_specific_title = fields.Boolean(
        string="Invoicing Address Specific Title",
        config_parameter='of.sale.report.setting.pdf_invoicing_address_specific_title',
    )
    pdf_invoicing_address_specific_title_label = fields.Char(
        string="Invoicing Address Specific Title Label",
        size=30,
        config_parameter='of.sale.report.setting.pdf_invoicing_address_specific_title_label',
    )
    pdf_shipping_address_specific_title = fields.Boolean(
        string="Shipping Address Specific Title",
        config_parameter='of.sale.report.setting.pdf_shipping_address_specific_title',
    )
    pdf_shipping_address_specific_title_label = fields.Char(
        string="Shipping Address Specific Title Label",
        size=30,
        config_parameter='of.sale.report.setting.pdf_shipping_address_specific_title_label',
    )
    pdf_invoicing_shipping_address_specific_title = fields.Boolean(
        string="Invoicing and Shipping Address Specific Title",
        config_parameter='of.sale.report.setting.pdf_invoicing_shipping_address_specific_title',
    )
    pdf_invoicing_shipping_address_specific_title_label = fields.Char(
        string="Invoicing and Shipping Address Specific Title Label",
        size=30,
        config_parameter='of.sale.report.setting.pdf_invoicing_shipping_address_specific_title_label',
    )

    # Salesperson information
    pdf_salesperson_info = fields.Boolean(
        string="Salesperson Information", config_parameter='of.sale.report.setting.pdf_salesperson_info'
    )
    pdf_salesperson_name = fields.Boolean(
        string="Salesperson Name", config_parameter='of.sale.report.setting.pdf_salesperson_name'
    )
    pdf_salesperson_phone = fields.Boolean(
        string="Salesperson Phone", config_parameter='of.sale.report.setting.pdf_salesperson_phone'
    )
    pdf_salesperson_mobile = fields.Boolean(
        string="Salesperson Mobile", config_parameter='of.sale.report.setting.pdf_salesperson_mobile'
    )
    pdf_salesperson_fax = fields.Boolean(
        string="Salesperson Fax", config_parameter='of.sale.report.setting.pdf_salesperson_fax'
    )
    pdf_salesperson_email = fields.Boolean(
        string="Salesperson Email", config_parameter='of.sale.report.setting.pdf_salesperson_email'
    )

    # Customer information
    pdf_customer_info = fields.Boolean(
        string="Customer Information", config_parameter='of.sale.report.setting.pdf_customer_info'
    )
    pdf_customer_phone = fields.Boolean(
        string="Customer Phone", config_parameter='of.sale.report.setting.pdf_customer_phone'
    )
    pdf_customer_mobile = fields.Boolean(
        string="Customer Mobile", config_parameter='of.sale.report.setting.pdf_customer_mobile'
    )
    pdf_customer_fax = fields.Boolean(string="Customer Fax", config_parameter='of.sale.report.setting.pdf_customer_fax')
    pdf_customer_email = fields.Boolean(
        string="Customer Email", config_parameter='of.sale.report.setting.pdf_customer_email'
    )

    # Other information
    pdf_payment_term_info = fields.Boolean(
        string="Payment terms", config_parameter='of.sale.report.setting.pdf_payment_term_info'
    )
    pdf_order_ref_info = fields.Boolean(
        string="Order reference", config_parameter='of.sale.report.setting.pdf_order_ref_info'
    )
    pdf_customer_ref_info = fields.Boolean(
        string="Customer reference", config_parameter='of.sale.report.setting.pdf_customer_ref_info'
    )
    pdf_validity_info = fields.Boolean(
        string="Validity date", config_parameter='of.sale.report.setting.pdf_validity_info'
    )

    # Sections
    pdf_section_bg_color = fields.Char(
        string="Background color",
        config_parameter='of.sale.report.setting.pdf_section_bg_color',
        help="Background color of the section headings. Default is white.",
    )
    pdf_section_font_color = fields.Char(
        string="Font color",
        config_parameter='of.sale.report.setting.pdf_section_font_color',
        help="Font color of the section headings. Default is black.",
    )

    # Order lines
    pdf_product_reference = fields.Boolean(
        string="Product reference", config_parameter='of.sale.report.setting.pdf_product_reference'
    )
    pdf_price_taxexcl = fields.Boolean(
        string="Price Tax Excl.", config_parameter='of.sale.report.setting.pdf_price_taxexcl'
    )
    pdf_price_taxinc = fields.Boolean(
        string="Price Tax Incl.", config_parameter='of.sale.report.setting.pdf_price_taxinc'
    )
    pdf_print_image_level = fields.Selection(
        selection=[
            ('no', "Do not print"),
            ('line', "Print on each line"),
            ('appendix', "Print on appendix"),
            ('line_appendix', "Print first image on line and others on appendix"),
        ],
        string="Product images",
        config_parameter='of.sale.report.setting.pdf_print_image_level',
        default='no',
    )
    module_of_sale_report_setting_product_multi_image = fields.Boolean(
        compute='_compute_module_of_sale_report_setting_product_multi_image', store=True, readonly=False
    )

    group_of_sale_report_print_attachment = fields.Boolean(
        string="Product attachments", implied_group='of_sale_report_setting.group_of_sale_report_print_attachment'
    )

    # Signatures insert
    pdf_signatures_insert = fields.Boolean(
        string="Signatures", config_parameter='of.sale.report.setting.pdf_signatures_insert'
    )
    pdf_customer_signature = fields.Boolean(
        string="Customer signature", config_parameter='of.sale.report.setting.pdf_customer_signature'
    )
    pdf_vendor_signature = fields.Boolean(
        string="Salesman signature", config_parameter='of.sale.report.setting.pdf_vendor_signature'
    )
    group_pdf_prefill_vendor_signature = fields.Boolean(
        string="Pre-filled salesman signature",
        implied_group='of_sale_report_setting.group_of_pdf_prefill_vendor_signature',
    )
    pdf_signature_text = fields.Boolean(
        string="Signature statement", config_parameter='of.sale.report.setting.pdf_signature_text'
    )
    pdf_signature_text_label = fields.Char(
        string="Signature statement label", config_parameter='of.sale.report.setting.pdf_signature_text_label'
    )

    @api.onchange('pdf_salesperson_info')
    def onchange_pdf_salesperson_info(self):
        # we have to check the value of the field before the onchange is applied, because when the form is loaded, the
        # onchange will update the value of the field even if it is not changed by the user
        origin_value = self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_salesperson_info')
        if not origin_value and self.pdf_salesperson_info and not self.pdf_salesperson_name:
            self.pdf_salesperson_name = True

    @api.onchange('pdf_signatures_insert')
    def _onchange_pdf_signatures_insert(self):
        # we have to check the value of the field before the onchange is applied, because when the form is loaded, the
        # onchange will update the value of the field even if it is not changed by the user
        origin_value = self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_signatures_insert')
        if not origin_value and self.pdf_signatures_insert and not self.pdf_customer_signature:
            self.pdf_customer_signature = True
        if not origin_value and self.pdf_signatures_insert and not self.pdf_vendor_signature:
            self.pdf_vendor_signature = True

    @api.depends('pdf_print_image_level')
    def _compute_module_of_sale_report_setting_product_multi_image(self):
        for wizard in self:
            if wizard.pdf_print_image_level in ['appendix', 'line_appendix']:
                wizard.module_of_sale_report_setting_product_multi_image = True

    @api.onchange('pdf_vendor_signature')
    def _onchange_pdf_vendor_signature(self):
        if not self.pdf_vendor_signature:
            self.group_pdf_prefill_vendor_signature = False

    def action_printings_params(self):
        return {
            'name': _("Configure PDF printing"),
            'type': 'ir.actions.act_window',
            'res_model': 'res.config.settings',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref('of_sale_report_setting.res_config_settings_sale_printing_params_view_form').id,
            'target': 'new',
        }
