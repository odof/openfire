# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    of_carrier_id = fields.Many2one(
        comodel_name='delivery.carrier', string=u"Coût de livraison estimé",
        domain="['|',('of_supplier_ids','=',partner_id),('of_use_purchase','=',True)]")
    of_franco = fields.Char(string="Franco de port", compute="_compute_of_franco")

    @api.depends('of_carrier_id', 'order_line', 'amount_total')
    def _compute_of_franco(self):
        for po in self:
            if not po.of_carrier_id or not po.order_line:
                continue
            weight = volume = quantity = 0
            total_delivery = 0.0
            for line in po.order_line:
                if line.state == 'cancel':
                    continue
                if line.of_is_delivery:
                    total_delivery += line.price_total
                if not line.product_id or line.of_is_delivery:
                    continue
                qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
                weight += (line.product_id.weight or 0.0) * qty
                volume += (line.product_id.volume or 0.0) * qty
                quantity += qty
            total = (po.amount_total or 0.0) - total_delivery
            total = po.currency_id.with_context(date=po.date_order).compute(total, po.company_id.currency_id)
            price = po.of_carrier_id.get_difference_from_picking(total, weight, volume, quantity)
            po.of_franco = u'Estimation %.2f%s' % (price, po.currency_id.symbol)
            pass

    @api.onchange('partner_id')
    def onchange_partner_id_dtype(self):
        if self.partner_id:
            self.of_carrier_id = self.partner_id.property_delivery_carrier_id

    @api.multi
    def _delivery_unset(self):
        self.env['purchase.order.line'].search([('order_id', 'in', self.ids), ('of_is_delivery', '=', True)]).unlink()

    @api.multi
    def delivery_set(self):

        # Remove delivery products from the sale order
        self._delivery_unset()

        for order in self:
            carrier = order.of_carrier_id
            if carrier:
                if order.state not in ('draft', 'sent'):
                    raise UserError(_('The order state have to be draft to add delivery lines.'))

                if carrier.delivery_type not in ['fixed', 'base_on_rule']:
                    # Shipping providers are used when delivery_type is other than 'fixed' or 'base_on_rule'
                    price_unit = carrier.get_shipping_price_from_so(order)[0]
                else:
                    # Classic grid-based carriers
                    carrier = carrier.verify_carrier(order.partner_id)
                    if not carrier:
                        raise UserError(_('No carrier matching.'))
                    price_unit = carrier.get_price_available_purchase(order)

                final_price = price_unit * (1.0 + (float(self.of_carrier_id.margin) / 100.0))
                order._create_delivery_line(carrier, final_price)

            else:
                raise UserError(_('No carrier set for this order.'))

        return True

    def _create_delivery_line(self, carrier, price_unit):
        PurchaseOrderLine = self.env['purchase.order.line']
        if self.partner_id:
            # set delivery detail in the customer language
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.supplier_taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, carrier.product_id, self.partner_id).ids

        # Create the purchase order line
        values = {
            'order_id': self.id,
            'name': carrier.with_context(lang=self.partner_id.lang).name,
            'product_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, taxes_ids)],
            'of_is_delivery': True,
            'date_planned': self.date_planned
        }
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        pol = PurchaseOrderLine.sudo().create(values)
        return pol


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_is_delivery = fields.Boolean(string="Is a Delivery", default=False)
