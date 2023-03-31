# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_cee_number = fields.Char(string=u"Numéro CEE")
    of_cee_invoice_status = fields.Selection(
        selection=[('no', u"Rien à facturer"),
                   ('to_invoice', u"À facturer"),
                   ('invoiced', u"Facturé")],
        compute='_compute_of_cee_invoice_status', string=u"État de facturation CEE", store=True)

    @api.depends(
        'state', 'order_line', 'order_line.product_id', 'order_line.product_id.categ_id', 'order_line.invoice_lines')
    def _compute_of_cee_invoice_status(self):
        cee_product_categ_id = self.env['ir.values'].get_default('sale.config.settings', 'of_cee_product_categ_id')
        for order in self:
            cee_lines = order.order_line.filtered(
                lambda l: l.product_id.categ_id.id == cee_product_categ_id and l.product_uom_qty)
            if not cee_lines or order.state != 'sale':
                order.of_cee_invoice_status = 'no'
            else:
                if cee_lines.filtered(
                        lambda l: not l.invoice_lines.filtered(lambda inv_line: inv_line.invoice_id.of_is_cee)):
                    order.of_cee_invoice_status = 'to_invoice'
                else:
                    order.of_cee_invoice_status = 'invoiced'

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_cee_number'] = self.of_cee_number
        return invoice_vals


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_cee_product_categ_id = fields.Many2one(
        comodel_name='product.category', string=u"(OF) Catégorie des articles CEE",
        help=u"Catégorie des articles utilisés pour les primes CEE")

    @api.multi
    def set_of_cee_product_categ_id_defaults(self):
        recompute_field = False
        if self.env['ir.values'].get_default('sale.config.settings', 'of_cee_product_categ_id') != \
                self.of_cee_product_categ_id.id:
            recompute_field = True
        res = self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_cee_product_categ_id', self.of_cee_product_categ_id.id)
        if recompute_field:
            # Recalcul du champ compute 'of_cee_invoice_status'
            self.env['sale.order'].search([])._compute_of_cee_invoice_status()
        return res
