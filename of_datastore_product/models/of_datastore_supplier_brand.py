# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _

from of_datastore_product import DATASTORE_IND


class OfDatastoreSupplierBrand(models.AbstractModel):
    _name = 'of.datastore.supplier.brand'

    name = fields.Char(string='Supplier brand', required=True, readonly=True)
    datastore_brand_id = fields.Integer(string='Supplier brand ID', required=True, readonly=True)
    brand_id = fields.Many2one('of.product.brand', string="Brand")
    product_count = fields.Integer(string='# Products', readonly=True)
    note_maj = fields.Text(string='Update notes', readonly=True)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        brand_obj = self.env['of.product.brand']
        ds_supplier_obj = self.env['of.datastore.supplier']
        default_ds_brand_name = _('Error')
        result = []
        for ds_brand_full_id in self.ids:
            ds_supplier_id = ds_brand_full_id / DATASTORE_IND
            ds_brand_id = ds_brand_full_id % DATASTORE_IND

            brand = brand_obj.search([
                ('datastore_supplier_id', '=', ds_supplier_id),
                ('datastore_brand_id', '=', ds_brand_id)])

            vals = {
                'id': ds_brand_full_id,
                'brand_id': brand and brand.id or False,
                'name': default_ds_brand_name,
                'datastore_brand_id': False,
                'note_maj': '',
                'product_count': False,
            }

            ds_supplier = ds_supplier_obj.browse(ds_supplier_id)
            client = ds_supplier.of_datastore_connect()
            if not isinstance(client, basestring):
                ds_brand_obj = ds_supplier.of_datastore_get_model(client, 'of.product.brand')
                ds_brand_data = ds_supplier.of_datastore_read(
                    ds_brand_obj, [ds_brand_id], ['name', 'note_maj', 'product_count'])[0]
                del ds_brand_data['id']
                vals.update(ds_brand_data)

            if fields:
                vals = {key: val for key, val in vals.iteritems() if key in fields}

            result.append(vals)
        return result

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if args and len(args) == 1 and args[0][0] == 'id':
            return args[0][2]
        return super(OfDatastoreSupplierBrand, self)._search(args, offset, limit, order, count, access_rights_uid)

    @api.multi
    def _write(self, vals):
        if self and vals and 'brand_id' in vals:
            brand_obj = self.env['of.product.brand']
            ds_brand_full_id = self.ids[0]
            ds_supplier_id = ds_brand_full_id / DATASTORE_IND
            ds_brand_id = ds_brand_full_id % DATASTORE_IND

            new_brand_id = vals['brand_id']
            old_brand = brand_obj.search(
                [('datastore_supplier_id', '=', ds_supplier_id),
                 ('datastore_brand_id', '=', ds_brand_id)])
            if new_brand_id == old_brand.id:
                return True
            if old_brand:
                old_brand.write({'datastore_supplier_id': False, 'datastore_brand_id': False})
                # On vide le champ of_datastore_res_id des articles de la marque qui n'est plus liée au TC.
                old_brand.product_ids.write({'of_datastore_res_id': False})
                old_brand.product_variant_ids.write({'of_datastore_res_id': False})
            if new_brand_id:
                new_brand = brand_obj.browse(new_brand_id)
                new_brand.write({'datastore_supplier_id': ds_supplier_id, 'datastore_brand_id': ds_brand_id})
                # On vide le champ of_datastore_res_id des articles de la marque nouvellement liée au TC.
                new_brand.product_ids.write({'of_datastore_res_id': False})
                new_brand.product_variant_ids.write({'of_datastore_res_id': False})

            # Mise à jour des demandes de connexion TC
            supplier = self.env['of.datastore.supplier'].browse(ds_supplier_id)
            datastore_brand = self.env['of.datastore.brand'].search(
                [('db_name', '=', supplier.db_name), ('datastore_brand_id', '=', ds_brand_id)])
            if datastore_brand:
                if new_brand_id:
                    datastore_brand.write({'brand_id': new_brand_id, 'state': 'connected'})
                else:
                    datastore_brand.write({'brand_id': False, 'state': 'available'})
        return True
