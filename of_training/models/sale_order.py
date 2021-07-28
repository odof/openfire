# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_training = fields.Boolean(string="Is training")
    is_subrogation = fields.Boolean(string="Subrogation")
    session_id = fields.Many2one("of.training.session", string="Session")
    organization_id = fields.Many2one("res.partner", string="Organization")
    organization_file_number = fields.Char(string="Organization file number")
    organization_file_date = fields.Date(string="Organization file date")


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.model
    def _default_of_subrogation_product_categ_id(self):
        category_id = self.env['ir.values'].get_default('sale.config.settings', 'of_subrogation_product_categ_id_setting')
        return self.env['product.category'].browse(category_id)

    @api.model
    def _default_of_subrogation_product_id(self):
        categ = self._default_of_subrogation_product_categ_id()
        products = categ and self.env['product.product'].search([('categ_id', '=', categ.id), ('type', '=', 'service')])
        return len(products) == 1 and products or self.env['product.product'].browse()

    @api.model
    def _default_of_opco_partner_id(self):
        order_id = self.env['sale.order'].browse(self._context.get('active_id', False))
        organization_id = order_id and order_id.organization_id
        return organization_id or self.env['res.partner'].browse()


    advance_payment_method = fields.Selection(selection_add=[('subrogation', 'Subrogation')])

    of_subrogation_product_categ_id = fields.Many2one("product.category", string="(OF) Subrogation category", default=_default_of_subrogation_product_categ_id)
    of_subrogation_product_id = fields.Many2one("product.product", string="(OF) Subrogation product", domain="[('categ_id', '=', of_subrogation_product_categ_id), ('type', '=', 'service')]", default=_default_of_subrogation_product_id)
    of_opco_partner_id = fields.Many2one("res.partner", string="(OF) OPCO organization", default=_default_of_opco_partner_id)
    of_subrogation_amount = fields.Float(string="(OF) Subrogation amount")


    @api.multi
    def _create_invoice(self, order, so_line, amount):
        if order.company_id:
            self = self.with_context(company_id=order.company_id.id, default_company_id=order.company_id.id)
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        # La méthode _onchange_tax est définie dans le module of_account_tax et recalcule le compte comptable de
        # la ligne de facture en fonction de ses taxes.
        for line in invoice.invoice_line_ids:
            line.onchange_tax_ids()
        # Modification du libellé de la ligne d'acompte
        if self._context.get('of_subrogation_line_name'):
            invoice.invoice_line_ids[0].name = self._context['of_subrogation_line_name']
        # Modification des informations relatives au partner_id
        if self._context.get('parner_id'):
            invoice.account_id = self._context['parner_id'].property_account_receivable_id.id
        if self._context.get('parner_id'):
            invoice.partner_id = self._context['partner_invoice_id'].id
        if self._context.get('parner_id'):
            invoice.partner_shipping_id = self._context['partner_shipping_id'].id

        return invoice

    @api.multi
    def create_invoices(self):

        if self.advance_payment_method == 'subrogation':
            if not self.of_subrogation_product_id:
                raise UserError(u"Vous devez sélectionner un article de subrogation")
            if not self.of_opco_partner_id:
                raise UserError(u"Vous devez sélectionner un organisme OPCO")

            self.product_id = self.of_subrogation_product_id
            self.amount = self.of_subrogation_amount
            partner_id = self.of_opco_partner_id
            amount_total = 0.0

            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

            for order in sale_orders:
                amount_total = amount_total + order.amount_untaxed

            if self.amount > amount_total:
                raise UserError(u"Vous ne pouvez pas faire une subrogation d'un montant supérieur à celui de la commande.")

            result = super(SaleAdvancePaymentInv, self.with_context(
                active_ids=order.ids,
                parner_id=partner_id,
                partner_invoice_id=partner_id,
                partner_shipping_id=partner_id,
                lang=partner_id.lang,
                of_subrogation_line_name=_("Subrogation of %s") % (self.amount),
            )).create_invoices()
        else:
            result = super(SaleAdvancePaymentInv, self).create_invoices()
        return result


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_subrogation_product_categ_id_setting = fields.Many2one("product.category", string="(OF)Subrogation category")

    @api.multi
    def set_of_subrogation_product_categ_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_subrogation_product_categ_id_setting', self.of_subrogation_product_categ_id_setting.id)