# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFCostRecomputeWizard(models.TransientModel):
    _inherit = 'of.cost.recompute.wizard'

    @api.model
    def default_get(self, field_list=None):
        res = super(OFCostRecomputeWizard, self).default_get(field_list)
        # Suivant que la prise de rdv se fait depuis la fiche client ou une demande d'intervention
        if self._context.get('active_model', '') == 'account.invoice':
            res['invoice_ids'] = self._context['active_ids']
        return res

    invoice_ids = fields.Many2many(comodel_name='account.invoice', string=u"Facture(s) concernée(s)")

    @api.multi
    def recompute_cost(self):
        super(OFCostRecomputeWizard, self).recompute_cost()
        if self.invoice_ids:
            self._recompute_invoice_costs()

    @api.multi
    def _recompute_invoice_costs(self):
        invoices = self.invoice_ids
        if hasattr(invoices, 'of_boutique'):
            invoices = invoices.filtered(lambda r: not r.of_boutique)
        invoice_lines = invoices.mapped('invoice_line_ids')
        if self.brand_ids:
            brand_ids = self.brand_ids._ids
            invoice_lines = invoice_lines.filtered(lambda r: r.product_id.brand_id.id not in brand_ids)
        if self.product_categ_ids:
            categ_ids = self.product_categ_ids._ids
            invoice_lines = invoice_lines.filtered(lambda r: r.product_id.categ_id.id not in categ_ids)
        if self.exclude_zero:
            invoice_lines = invoice_lines.filtered('of_unit_cost')
        self._handle_invoice_lines(invoice_lines)

    @api.multi
    def _handle_invoice_lines(self, invoice_lines):
        field_used = self.cost_method
        for line in invoice_lines:
            cost = 0
            purchase_price = 0
            if line.of_is_kit:
                if len(line.sale_line_ids) == 1 and line.sale_line_ids.of_is_kit:
                    cost = line.sale_line_ids.purchase_price
                    purchase_price = line.sale_line_ids.of_seller_price
                else:
                    for kit_line in line.kit_id.kit_line_ids:
                        if self.real_cost and kit_line.order_comp_id.procurement_ids:
                            purchase_lines = kit_line.order_comp_id.procurement_ids.mapped(
                                'move_ids.move_orig_ids.purchase_line_id')
                            purchase_lines |= kit_line.order_comp_id.procurement_ids.mapped(
                                'move_ids.purchase_line_id')
                            purchase_price_subtotal = sum(purchase_lines.mapped('price_subtotal'))
                            purchase_qty = sum(purchase_lines.mapped('product_qty'))
                            purchase_unit_price = purchase_price_subtotal / purchase_qty if purchase_qty else 0.0
                            purchase_cost = purchase_unit_price * line.product_id.property_of_purchase_coeff
                            sale_qty = kit_line.order_comp_id.qty_per_kit
                            if sale_qty and purchase_qty < sale_qty:
                                cost_line = (
                                    (
                                        (purchase_cost * purchase_qty) +
                                        (line.sale_line_ids.purchase_price * (sale_qty - purchase_qty))
                                    ) / sale_qty)
                                purchase_price += (
                                    (
                                        (purchase_unit_price * purchase_qty) +
                                        (line.sale_line_ids.of_seller_price * (sale_qty - purchase_qty))
                                    ) / sale_qty)
                            else:
                                cost_line = purchase_cost
                                purchase_price += purchase_unit_price

                        else:
                            cost_line = kit_line.product_id[field_used]
                            purchase_price += kit_line.product_id.of_seller_price
                        if self.exclude_change_zero and not cost:
                            kit_line.cost_unit = cost_line
                            cost += cost_line
                        elif not self.exclude_change_zero:
                            kit_line.cost_unit = cost_line
                            cost += cost_line
            else:
                if self.real_cost and len(line.sale_line_ids) == 1:
                    purchase_lines = line.sale_line_ids.mapped(
                        'procurement_ids.move_ids.move_orig_ids.purchase_line_id')
                    purchase_lines |= line.sale_line_ids.mapped('procurement_ids.move_ids.purchase_line_id')
                    purchase_price_subtotal = sum(purchase_lines.mapped('price_subtotal'))
                    purchase_qty = sum(purchase_lines.mapped('product_qty'))
                    purchase_unit_price = purchase_price_subtotal / purchase_qty if purchase_qty else 0.0
                    purchase_cost = purchase_unit_price * line.product_id.property_of_purchase_coeff
                    sale_qty = line.sale_line_ids.product_uom_qty
                    if sale_qty and purchase_qty < sale_qty:
                        cost = ((purchase_cost * purchase_qty) +
                                (line.sale_line_ids.purchase_price * (sale_qty - purchase_qty))) / sale_qty
                        purchase_price = ((purchase_unit_price * purchase_qty) +
                                          (line.sale_line_ids.of_seller_price * (sale_qty - purchase_qty))) / sale_qty
                    else:
                        cost = purchase_cost
                        purchase_price = purchase_unit_price
                if not cost:
                    cost = line.product_id[field_used]
                if not purchase_price:
                    purchase_price = line.product_id.of_seller_price
            if not (self.exclude_change_zero and not cost):
                line.of_unit_cost = cost
            if not (self.exclude_change_zero and not purchase_price):
                line.of_purchase_price = purchase_price
