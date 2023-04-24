# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def pdf_address_title(self):  # same as sale_order.py
        return self.env['ir.config_parameter'].sudo().get_param('of.sale.report.setting.pdf_address_title')

    def pdf_invoicing_address_specific_title(self):  # same as sale_order.py
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_address_specific_title')
        )

    def pdf_invoicing_address_specific_title_label(self):  # same as sale_order.py
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_address_specific_title_label')
        )

    def pdf_shipping_address_specific_title(self):  # same as sale_order.py
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_shipping_address_specific_title')
        )

    def pdf_shipping_address_specific_title_label(self):  # same as sale_order.py
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_shipping_address_specific_title_label')
        )

    def pdf_invoicing_shipping_address_specific_title(self):  # same as sale_order.py
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_shipping_address_specific_title')
        )

    def pdf_invoicing_shipping_address_specific_title_label(self):  # same as sale_order.py
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('of.sale.report.setting.pdf_invoicing_shipping_address_specific_title_label')
        )
