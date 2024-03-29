# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from datetime import datetime, date, timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_website_commitment_date = fields.Datetime(
        string='Website Commitment Date', help="Date by which the products are sure to be delivered."
        "This is a date that you can promise to the customer, based on the Product Lead Times.")

    def _compute_of_website_commitment_date(self):
        """Compute the website commitment date, only called on /shop/payment from the website"""

        # On récupère le site web
        website = self.env['website'].search([])[0]
        of_delivery_management = website.get_of_delivery_management()

        for order in self:

            if not of_delivery_management:
                order.of_website_commitment_date = False
                continue

            dates_list = []

            # Avec le test sur sale_ok, on exclue la ligne qui corrrespond à la livraison
            for line in order.order_line.filtered(lambda x: x.state != 'cancel' and x.product_id.sale_ok is True):

                # On récupère la date de livraison pour cette ligne
                dt = line.get_delivery_date()
                dates_list.append(dt)

            if dates_list:
                # On détermine la commitment_date en fonction de la picking policy
                commit_date = min(dates_list) if order.picking_policy == 'direct' else max(dates_list)
                order.of_website_commitment_date = fields.Datetime.to_string(commit_date)

                # Si la requested_date n'est plus à jour, on la met à jour
                if order.requested_date:
                    order.requested_date = fields.Datetime.to_string(max([
                        fields.Datetime.from_string(order.requested_date),
                        fields.Datetime.from_string(order.of_website_commitment_date)
                    ]))

    # Add a depends on picking_policy
    @api.depends('date_order', 'picking_policy', 'order_line.customer_lead')
    def _compute_commitment_date(self):
        """Compute the commitment date"""
        for order in self:
            dates_list = []
            order_datetime = fields.Datetime.from_string(order.date_order)

            # Si c'est une commande website, le of_website_commitment_date est défini et vient remplir le commitment_date
            if order.of_website_commitment_date:
                order.commitment_date = order.of_website_commitment_date
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

        # Si gestion des stocks et interdit de commander stock non disponible et pas d'exception sur l'article
        if website.get_website_config() != 'none' and website.get_of_unavailability_management() == 'notify' \
                and product.availability is False:

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

    def get_quantity_available(self):
        # On récupère le site web
        website = self.env['website'].search([], limit=1)

        # On calcul le product_quantity en fonction de la configuration on_hand/forecast
        quantity_available = self.product_id.qty_available
        if website.get_website_config() == 'forecast':
            quantity_available += - self.product_id.outgoing_qty + self.product_id.incoming_qty

        return quantity_available or 0

    def get_days_of_delay(self):
        # On récupère le site web
        website = self.env['website'].search([], limit=1)

        # On calcul le days_of_delay en fonction de la quantity_available
        days_of_delay = float(max(self.customer_lead, website.get_of_website_security_lead()) or 0.0)
        if self.product_uom_qty > self.get_quantity_available():
            days_of_delay += (website.company_id.security_lead or 0.0) + (self.product_id._select_seller(
                quantity=self.product_uom_qty, uom_id=self.product_uom).delay or 0.0)

        return days_of_delay or 0.0

    def get_delivery_date(self):
        # On calcul le delivery_date en fonction du days_of_delay
        return datetime.now() + timedelta(days=self.get_days_of_delay())


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # On met le default à vide
    availability = fields.Selection(
        help=u"Laisser vide pour une gestion standard des stock sur le site web, le remplir rajoute une exception sur "
             u"cet article et permet de ne pas gérer les stocks. 'Ne rien afficher' n'affiche aucun message, "
             u"'En stock' affiche un message 'En stock', 'Avertissement' affiche le message de votre choix.",
        default=False)
