# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_datastore_order = fields.Boolean(string=u"Commande auto", copy=False)

    @api.multi
    def action_confirm(self):
        datastore_obj = self.env['of.datastore.sale']
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.of_datastore_purchase_id:
                continue
            datastore = datastore_obj.search([('partner_id', '=', order.partner_id.id)])
            client = datastore.of_datastore_connect()
            if not isinstance(client, basestring):
                ds_po_obj = datastore.of_datastore_get_model(client, 'purchase.order')
                datastore.of_datastore_func(ds_po_obj, 'button_confirm_xmlrpc', [order.of_datastore_purchase_id], [])
        return res


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_datastore_sale_misc_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article divers pour le connecteur vente",
        help=u"Article utilisé par le connecteur vente si aucun article ne correspond à la référence reçue")
    group_of_group_datastore_brand_dropshipping = fields.Boolean(
        string="(OF) Livraison directe", help="Autorise l'utilisation de la livraison directe sur les marques.",
        implied_group='of_datastore_sale.of_group_datastore_brand_dropshipping')

    @api.multi
    def set_of_datastore_sale_misc_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_datastore_sale_misc_product_id', self.of_datastore_sale_misc_product_id.id)
