# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = "product.category"

    type = fields.Selection([
        ('view', 'Vue'),
        ('normal', 'Normale'),
        ('escompte', 'Escompte')])


class ProductTemplate(models.Model):
    _inherit = "product.template"

    categ_id = fields.Many2one(domain="[('type','in',('normal', 'escompte'))]")


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    of_type_escompte = fields.Boolean(string=u"Type escompte", compute="_is_escompte")

    @api.depends('product_id')
    def _is_escompte(self):
        for line in self:
            line.of_type_escompte = line.product_id and line.product_id.categ_id.type == "escompte"

    @api.onchange('price_unit', 'quantity', 'of_type_escompte')
    def _onchange_detect_non_negative_escompte(self):
        if self.price_unit * self.quantity > 0 and self.of_type_escompte:
            self.price_unit = 0
            warning = {
                'title': ('Attention!'),
                'message': (u"Le montant de l'escompte doit être négatif"),
            }
            return {'warning': warning}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_reduction = fields.Boolean(string=u"Escompte")
    of_reduction_perc = fields.Float(string=u"Pourcentage de l'escompte")

    @api.onchange('of_reduction')
    def _onchange_of_reduction(self):
        if self.of_reduction:
            self.of_reduction_perc = self.env['ir.values'].get_default(
                'sale.config.settings', 'of_default_reduction_perc')

    @api.multi
    def get_lines_for_reduction(self):
        self.ensure_one()
        reduction_product_id = self.env['ir.values'].get_default('sale.config.settings', 'of_reduction_product_id')
        return self.order_line.filtered(lambda l: l.product_id.id != reduction_product_id)

    @api.multi
    def set_reduction(self):

        for order in self:
            reduction_product_id = self.env['ir.values'].get_default('sale.config.settings', 'of_reduction_product_id')
            reduction_product = self.env['product.product'].browse([reduction_product_id])
            if reduction_product:
                if not order.of_reduction_perc:
                    raise UserError(u"Veuillez indiquer un pourcentage pour l'escompte.")
                else:
                    # Compute order untaxed amount
                    lines = order.get_lines_for_reduction()
                    untaxed_amount = sum(lines.mapped('price_subtotal'))

                    # Compute reduction amount
                    reduction_price = untaxed_amount * (order.of_reduction_perc / 100.0)

                    # Check if reduction line already exists
                    reduction_line = order.order_line.filtered(lambda l: l.product_id.id == reduction_product_id)
                    if reduction_line:
                        reduction_line.price_unit = -reduction_price
                    else:
                        # Apply fiscal position
                        taxes = reduction_product.taxes_id.filtered(lambda t: t.company_id.id == order.company_id.id)
                        taxes_ids = taxes.ids
                        if order.partner_id and order.fiscal_position_id:
                            taxes_ids = order.fiscal_position_id.map_tax(taxes, reduction_product, order.partner_id).ids

                        # Create the sale order line
                        values = {
                            'order_id': order.id,
                            'name': reduction_product.name,
                            'product_uom_qty': 1,
                            'product_uom': reduction_product.uom_id.id,
                            'product_id': reduction_product.id,
                            'price_unit': -reduction_price,
                            'tax_id': [(6, 0, taxes_ids)],
                        }
                        if order.order_line:
                            values['sequence'] = order.order_line[-1].sequence + 1
                        self.env['sale.order.line'].create(values)
            else:
                raise UserError(u"Aucun artcile d'escompte n'est défini.")

        return True


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_reduction_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article d'escompte", help=u"Article utilisé pour les escomptes",
        domain="[('categ_id.type', '=', 'escompte')]")
    of_default_reduction_perc = fields.Float(string=u"(OF) Pourcentage d'escompte par défaut")

    @api.multi
    def set_of_reduction_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_reduction_product_id', self.of_reduction_product_id.id)

    @api.multi
    def set_of_default_reduction_perc_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_default_reduction_perc', self.of_default_reduction_perc)
