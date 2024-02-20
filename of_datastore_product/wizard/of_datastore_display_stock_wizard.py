# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfDatastoreDisplayStock(models.TransientModel):
    _name = 'of.datastore.display.stock'

    @api.model
    def default_get(self, fields_list):
        res = super(OfDatastoreDisplayStock, self).default_get(fields_list)
        if self._context.get('active_ids') and self._context.get('active_model'):
            product = self.env[self._context['active_model']].browse(self._context['active_ids'][0])
            if product.of_datastore_res_id and product.brand_id.datastore_supplier_id:
                supplier = product.brand_id.datastore_supplier_id
                # Try except au cas où on ne peut pas atteindre la base centralisée,
                # pas d'erreur à envoyer, ne pas afficher d'erreur
                try:
                    client = supplier.of_datastore_connect()
                    if isinstance(client, basestring):
                        res['of_stock_informations'] = u"Impossible de se connecter au tarif centralisé."
                        return res
                    ds_product_obj = supplier.of_datastore_get_model(client, 'product.template')
                    qty_values = supplier.of_datastore_func(
                        ds_product_obj,
                        'of_datastore_get_quantities',
                        [product.of_datastore_res_id],
                        [])
                    res['qty_available'] = qty_values[0]
                    res['of_stock_informations'] = qty_values[1]
                except Exception:
                    res['of_stock_informations'] = u"Une erreur s'est produite."
        return res

    qty_available = fields.Float(string=u"Qté. Disponible")
    of_stock_informations = fields.Text(string="Informations de stock")
