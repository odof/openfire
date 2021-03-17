# -*- coding: utf-8 -*-

from odoo import models, fields, api


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
                # Le mouvement est déjà lié à une commande
                continue
            if not move.of_purchase_id:
                continue
            if move.picking_id.picking_type_code != 'incoming':
                continue
            product = move.product_id
            for purchase_line in move.of_purchase_id.order_line:
                if purchase_line.product_id == product and not purchase_line.move_ids:
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
        """
        :return: Dictionnaire de valeurs pour la création d'une ligne de commande d'achat.
        """
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

    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if 'product_uom_qty' in vals:
            # Mise à jour des quantités des lignes d'achat associées
            for purchase_line in self.mapped('purchase_line_id'):
                purchase_line.product_qty = sum(purchase_line.move_ids.mapped('product_uom_qty'))
        return res
