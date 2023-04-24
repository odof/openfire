# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def pdf_address_title(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_title')

    def pdf_address_contact_titles(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_titles')

    def pdf_address_contact_parent_name(self):
        return (
            self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_parent_name')
        )

    def pdf_address_contact_name(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_name')

    def pdf_address_contact_phone(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_phone')

    def pdf_address_contact_mobile(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_mobile')

    def pdf_address_contact_fax(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_fax')

    def pdf_address_contact_email(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_email')

    def pdf_invoicing_address_specific_title(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_address_specific_title')
        )

    def pdf_invoicing_address_specific_title_label(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_address_specific_title_label')
        )

    def pdf_shipping_address_specific_title(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_shipping_address_specific_title')
        )

    def pdf_shipping_address_specific_title_label(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_shipping_address_specific_title_label')
        )

    def pdf_invoicing_shipping_address_specific_title(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_shipping_address_specific_title')
        )

    def pdf_invoicing_shipping_address_specific_title_label(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_shipping_address_specific_title_label')
        )

    def pdf_salesperson_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_salesperson_info')

    def pdf_salesperson_name(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_salesperson_name')

    def pdf_salesperson_phone(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_salesperson_phone')

    def pdf_salesperson_mobile(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_salesperson_mobile')

    def pdf_salesperson_fax(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_salesperson_fax')

    def pdf_salesperson_email(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_salesperson_email')

    def pdf_customer_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_customer_info')

    def pdf_customer_phone(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_customer_phone')

    def pdf_customer_mobile(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_customer_mobile')

    def pdf_customer_fax(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_customer_fax')

    def pdf_customer_email(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_customer_email')

    def pdf_payment_term_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_payment_term_info')

    def pdf_order_ref_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_order_ref_info')

    def pdf_customer_ref_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_customer_ref_info')

    def pdf_validity_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_validity_info')

    def get_color_section(self):
        return (
            self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_section_bg_color', '#FFFFFF')
        )

    def get_color_font(self):
        return (
            self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_section_font_color', '#000000')
        )

    def pdf_price_taxexcl(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_price_taxexcl')

    def pdf_price_taxinc(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_price_taxinc')

    def pdf_print_image_level(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_print_image_level')

    def pdf_signatures_insert(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_signatures_insert')

    def pdf_customer_signature(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_customer_signature')

    def pdf_vendor_signature(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_vendor_signature')

    def pdf_prefill_vendor_signature(self):
        return self.env.user.has_group('of_sale_report_setting.group_of_pdf_prefill_vendor_signature')

    def pdf_signature_text(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_signature_text')

    def pdf_signature_text_label(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_signature_text_label')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_display_name = fields.Text(string="Display name for reports", compute='_compute_of_display_name')
    of_product_attachment_domain_ids = fields.One2many(
        comodel_name='ir.attachment',
        string="Product attachments domain",
        compute='_compute_of_product_attachment_domain_ids',
    )
    of_product_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Product attachments",
        compute='_compute_of_product_attachment_ids',
        readonly=False,
        store=True,
        domain="[('id', 'in', of_product_attachment_domain_ids)]",
    )

    def _compute_of_display_name(self):
        # Inhiber l'affichage de la référence
        display_ref = self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_product_reference')
        for line in self:
            name = line.with_context(lang=line.order_id.partner_id.lang, partner=line.order_id.partner_id.id).name
            if not display_ref and name.startswith("["):
                splitted = name.split("]")
                if len(splitted) > 1:
                    splitted.pop(0)
                    name = ']'.join(splitted).strip()
            line.of_display_name = name

    @api.depends('product_id')
    def _compute_of_product_attachment_domain_ids(self):
        if self.env.user.has_group('of_sale_report_setting.group_of_sale_report_print_attachment'):
            for line in self:
                product_ids = self.env['product.product'].search(
                    [('product_tmpl_id', '=', line.product_template_id.id)]
                )
                domain = [
                    '&',
                    ('mimetype', '=', 'application/pdf'),
                    '|',
                    '&',
                    ('res_model', '=', 'product.template'),
                    ('res_id', '=', line.product_template_id.id),
                    '&',
                    ('res_model', '=', 'product.product'),
                    ('res_id', 'in', product_ids.ids),
                ]
                attachments = self.env['ir.attachment'].search(domain)
                line.of_product_attachment_domain_ids = attachments
        else:
            for line in self:
                line.of_product_attachment_domain_ids = False

    @api.depends('product_id')
    def _compute_of_product_attachment_ids(self):
        if self.env.user.has_group('of_sale_report_setting.group_of_sale_report_print_attachment'):
            for line in self:
                attachment_ids = self.env['ir.attachment'].search(
                    [('id', 'in', line.of_product_attachment_domain_ids.ids)]
                )
                line.of_product_attachment_ids = [Command.set(attachment_ids.ids)]
        else:
            for line in self:
                line.of_product_attachment_ids = False
