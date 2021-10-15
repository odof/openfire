# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_commitment_date = fields.Datetime(string='Website Commitment Date',
        help="Date by which the products are sure to be delivered. This is a date that you can "
             "promise to the customer, based on the Product Lead Times.")

    def _compute_website_commitment_date(self):
        """Compute the website commitment date, only called on /shop/payment from the website"""

        # On récupère le site web
        website = self.env['website'].search([])[0]
        of_website_security_lead = float(website.get_of_website_security_lead()) or 0

        for order in self:
            dates_list = []
            order_datetime = fields.Datetime.from_string(order.date_order)
            # Avec le test sur sale_ok, on exclue la ligne qui corrrespond à la livraison
            for line in order.order_line.filtered(lambda x: x.state != 'cancel' and x.product_id.sale_ok is True):

                # On calcul le product_quantity en fonction de la configuration on_hand/forecast
                product_quantity = line.product_id.qty_available
                if website.get_website_config() == 'forecast':
                    product_quantity += - line.product_id.outgoing_qty + line.product_id.incoming_qty

                # On prend le max entre customer_lead et of_website_security_lead
                days = max(line.customer_lead, of_website_security_lead) or 0.0

                # Si article indisponible, on rajoute le délai fournisseur et la marge de sécurité
                if not product_quantity > 0:
                    days += (website.company_id.security_lead + line.product_id._select_seller(
                        quantity=line.product_qty, uom_id=line.product_uom).delay) \
                            or 0.0

                dt = order_datetime + timedelta(days=days)
                dates_list.append(dt)

            if dates_list:
                # On détermine la commitment_date en fonction de la picking policy
                commit_date = min(dates_list) if order.picking_policy == 'direct' else max(dates_list)
                order.website_commitment_date = fields.Datetime.to_string(commit_date)

    # Add a depends on picking_policy
    @api.depends('date_order', 'picking_policy', 'order_line.customer_lead')
    def _compute_commitment_date(self):
        """Compute the commitment date"""
        for order in self:
            dates_list = []
            order_datetime = fields.Datetime.from_string(order.date_order)

            # Si c'est une commande website, le website_commitment_date est défini et vient remplir le commitment_date
            if order.website_commitment_date:
                order.commitment_date = order.website_commitment_date
            else:
                for line in order.order_line.filtered(lambda x: x.state != 'cancel'):
                    dt = order_datetime + timedelta(days=line.customer_lead or 0.0)
                    dates_list.append(dt)
                if dates_list:
                    commit_date = min(dates_list) if order.picking_policy == 'direct' else max(dates_list)
                    order.commitment_date = fields.Datetime.to_string(commit_date)

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, attributes=None, **kwargs):
        res = super(SaleOrder, self)._cart_update(
            product_id=product_id, line_id=line_id,
            add_qty=add_qty, set_qty=set_qty, attributes=attributes, **kwargs)

        # On récupère le site web
        website = self.env['website'].search([])[0]

        product = self.env['product.product'].browse(int(product_id))

        # Si gestion des stocks et interdit de commander stock non disponible
        if website.get_website_config() != 'none' and website.get_of_unavailability_management() == 'notify':

            # On calcul le product_quantity en fonction de la configuration on_hand/forecast
            product_quantity = product.qty_available
            if website.get_website_config() == 'forecast':
                product_quantity += - product.outgoing_qty + product.incoming_qty

            # Si la quantité en panier est supérieure à la quantité disponible, on modifie par la quantité disponible
            if res['quantity'] > product_quantity:
                self.env['sale.order.line'].browse(int(res['line_id'])).write({
                    'product_uom_qty': product_quantity,
                })

        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id')
    def _compute_product_id_set_customer_lead(self):
        self.customer_lead = self.product_id.sale_delay


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # On met le default à vide
    availability = fields.Selection(default='')
