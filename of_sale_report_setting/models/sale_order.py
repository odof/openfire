# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_technical_visit_date = fields.Date(  # TODO: move me to of_sale module when it will migrated
        string="Technical Visit Date", help=u"If filled, it will be displayed in quotation/order report")

    def pdf_address_title(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_title')

    def pdf_address_contact_titles(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_contact_titles')

    def pdf_address_contact_parent_name(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_address_contact_parent_name')

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
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_invoicing_address_specific_title')

    def pdf_invoicing_address_specific_title_label(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_invoicing_address_specific_title_label')

    def pdf_shipping_address_specific_title(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_shipping_address_specific_title')

    def pdf_shipping_address_specific_title_label(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_shipping_address_specific_title_label')

    def pdf_invoicing_shipping_address_specific_title(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_invoicing_shipping_address_specific_title')

    def pdf_invoicing_shipping_address_specific_title_label(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_invoicing_shipping_address_specific_title_label')

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

    def pdf_technical_visit_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_technical_visit_info')

    def pdf_validity_info(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_validity_info')

    def get_color_section(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_section_bg_color', '#FFFFFF')

    def get_color_font(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.report.setting.pdf_section_font_color', '#000000')

    def pdf_price_taxexcl(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_price_taxexcl')

    def pdf_price_taxinc(self):
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_price_taxinc')

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

    of_price_unit_taxexcl = fields.Float(  # TODO: move me to of_sale module when it will be migrated
        string='Unit Price Tax excl', compute='_compute_of_price_unit', digits='Product Price', store=True,
        help="Unit price without taxes")
    of_price_unit_taxinc = fields.Float(  # TODO: move me to of_sale module when it will be migrated
        string='Unit Price Tax incl', compute='_compute_of_price_unit', digits='Product Price', store=True,
        help="Unit price with taxes")
    of_display_name = fields.Text(string="Display name for reports", compute='_compute_of_display_name')

    # TODO: move me to of_sale module when it will migrated
    @api.depends('price_unit', 'product_id', 'tax_id', 'currency_id', 'order_id.partner_shipping_id')
    def _compute_of_price_unit(self):
        for line in self:
            prices = line.tax_id.compute_all(
                line.price_unit, currency=line.currency_id, quantity=1, product=line.product_id,
                partner=line.order_id.partner_shipping_id)
            line.of_price_unit_taxexcl = prices['total_excluded']
            line.of_price_unit_taxinc = prices['total_included']

    def _compute_of_display_name(self):
        # Inhiber l'affichage de la référence
        display_ref = self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_product_reference')
        for line in self:
            name = line.with_context(lang=line.order_id.partner_id.lang, partner=line.order_id.partner_id.id).name
            if not display_ref:
                if name.startswith("["):
                    splitted = name.split("]")
                    if len(splitted) > 1:
                        splitted.pop(0)
                        name = ']'.join(splitted).strip()
            line.of_display_name = name
