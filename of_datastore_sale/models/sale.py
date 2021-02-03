# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_datastore_order = fields.Boolean(string=u"Commande auto", copy=False)


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_datastore_sale_misc_product_id = fields.Many2one(
        comodel_name='product.product', string=u"(OF) Article divers pour le connecteur vente",
        help=u"Article utilisé par le connecteur vente si aucun article ne correspond à la référence reçue")

    @api.multi
    def set_of_datastore_sale_misc_product_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_datastore_sale_misc_product_id', self.of_datastore_sale_misc_product_id.id)
