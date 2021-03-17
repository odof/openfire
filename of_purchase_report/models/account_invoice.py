# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    of_purchase_id = fields.Many2one(
        'purchase.order', string="Associer à la commande fournisseur",
        compute='_compute_of_purchase_id', inverse='_inverse_of_purchase_id', store=True
    )

    @api.depends('purchase_line_id')
    def _compute_of_purchase_id(self):
        for line in self:
            line.of_purchase_id = line.purchase_line_id.order_id

    def _inverse_of_purchase_id(self):
        purchase_line_obj = self.env['purchase.order.line']
        for inv_line in self:
            if not inv_line.of_purchase_id:
                continue
            product = inv_line.product_id
            for purchase_line in inv_line.of_purchase_id.order_line:
                if purchase_line.product_id == product and not purchase_line.invoice_lines:
                    # La ligne de commande a le même article : on l'associe à la ligne de facture
                    inv_line.purchase_line_id = purchase_line
                    break
            else:
                # Aucune ligne de commande n'a le même article que la ligne de facture
                # On crée donc une nouvelle ligne de commande
                purchase_line_data = inv_line._of_prepare_purchase_order_line(inv_line.of_purchase_id)
                purchase_line_obj.create(purchase_line_data)

    @api.multi
    def _of_prepare_purchase_order_line(self, purchase_order):
        self.ensure_one()
        return {
            'order_id': purchase_order.id,
            'name': self.name,
            'product_qty': self.quantity,
            'product_id': self.product_id.id,
            'product_uom': self.uom_id.id,
            'price_unit': self.price_unit,
            'date_planned': fields.Datetime.now(),
            'taxes_id': [(6, 0, self.invoice_line_tax_ids.ids)],
            'invoice_lines': [(4, self.id)],
        }
