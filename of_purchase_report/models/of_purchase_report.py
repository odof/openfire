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
                if purchase_line.product_id == product:
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


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_purchase_id = fields.Many2one(
        'purchase.order', string="Associer à la commande fournisseur",
        compute='_compute_of_purchase_id', inverse='_inverse_of_purchase_id', store=True
    )

    @api.depends('purchase_line_id')
    def _compute_of_purchase_id(self):
        for move in self:
            move.of_purchase_id = move.purchase_line_id.order_id

    def _inverse_of_purchase_id(self):
        purchase_line_obj = self.env['purchase.order.line']
        for move in self:
            if move.purchase_line_id:
                # Le mouvement est déjà liée à une commande
                continue
            if not move.of_purchase_id:
                continue
            if move.picking_id.picking_type_code != 'incoming':
                continue
            product = move.product_id
            for purchase_line in move.of_purchase_id.order_line:
                if purchase_line.product_id == product:
                    # La ligne de commande a le même article : on l'associe au mouvement de stock
                    move.purchase_line_id = purchase_line
                    break
            else:
                # Aucune ligne de commande n'a le même article que le mouvement de stock
                # On crée donc une nouvelle ligne de commande
                purchase_line_data = move._of_prepare_purchase_order_line(move.of_purchase_id)
                purchase_line_obj.create(purchase_line_data)

    @api.multi
    def _of_prepare_purchase_order_line(self, purchase_order):
        # Code récupéré du module purchase : procurement.order._prepare_purchase_order_line()
        self.ensure_one()

        product_uom_po_qty = self.product_uom._compute_quantity(self.product_qty, self.product_id.uom_po_id)
        seller = self.product_id._select_seller(
            partner_id=purchase_order.partner_id,
            quantity=product_uom_po_qty,
            date=self.date_expected,
            uom_id=self.product_id.uom_po_id)

        taxes = self.product_id.supplier_taxes_id
        fpos = purchase_order.fiscal_position_id
        taxes = fpos.map_tax(taxes) if fpos else taxes

        price_unit = self.env['account.tax']._fix_tax_included_price_company(
            seller.price, self.product_id.supplier_taxes_id, taxes, self.company_id) if seller else 0.0
        if price_unit and seller and purchase_order.currency_id and seller.currency_id != purchase_order.currency_id:
            price_unit = seller.currency_id.compute(price_unit, purchase_order.currency_id)

        product_lang = self.product_id.with_context({
            'lang': purchase_order.partner_id.lang,
            'partner_id': purchase_order.partner_id.id,
        })
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        return {
            'order_id': purchase_order.id,
            'name': name,
            'product_qty': product_uom_po_qty,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': self.date_expected,
            'taxes_id': [(6, 0, taxes.ids)],
            'move_ids': [(4, self.id)],
        }
