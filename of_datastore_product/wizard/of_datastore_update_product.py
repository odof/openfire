# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from ..models.of_datastore_product import DATASTORE_IND
import itertools
from odoo.exceptions import ValidationError

class OfDatastoreUpdateProduct(models.TransientModel):
    _name = "of.datastore.update.product"
    _description = 'Import / update products'

    def _default_is_update(self):
        active_ids = self._context.get('active_ids') or [0]
        return max(active_ids) > 0

    noup_name = fields.Boolean(string='Don\'t update product name')
    is_update = fields.Boolean('Show update options', default=lambda self: self._default_is_update())

    def _update_supplier_products(self, supplier, products):
        """
        Met à jour les produits products depuis la base fournisseur supplier
        @param supplier: browse_record of_datastore_supplier
        @param products: browse_record_list product.product
        """
        product_obj = self.env['product.product']

        supplier_value = supplier.id * DATASTORE_IND
        no_match_ids = [product.id for product in products if not product.of_datastore_res_id]
        id_match = {product.of_datastore_res_id: product
                    for product in products if product.of_datastore_res_id}

        # Certaines références ont pu être supprimées de la base centrale
        client = supplier.of_datastore_connect()
        ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
        ds_product_ids = supplier.with_context(active_test=False).of_datastore_search(ds_product_obj, [('id', 'in', id_match.keys())])

        no_match_ids += [id_match[ds_product_id].id for ds_product_id in id_match if ds_product_id not in ds_product_ids]

        # --- Matching des références avec la base centrale ---
        # Conversion des références article
        convert_func = supplier.get_product_code_convert_func()
        code_to_match_dict = {convert_func[product.brand_id](product.default_code): product
                              for product in product_obj.browse(no_match_ids)}
        # Récupération des correspondances de la base centrale
        ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
        ds_product_new_ids = supplier.of_datastore_search(ds_product_obj, [('default_code', 'in', code_to_match_dict.keys())])
        if ds_product_new_ids:
            for ds_product_data in supplier.of_datastore_read(ds_product_obj, ds_product_new_ids, ['default_code']):
                product = code_to_match_dict[ds_product_data['default_code']]

                no_match_ids.remove(product.id)
                if ds_product_data['id'] in id_match:
                    raise ValidationError(_('Two products try to reference the same centralized product : [%s] [%s]') %
                                          (product.default_code, id_match[ds_product_id].default_code))
                product.of_datastore_res_id = ds_product_data['id']
                id_match[ds_product_data['id']] = product
        ds_product_ids += ds_product_new_ids

        # --- Mise à jour des articles ---
        fields_to_update = product_obj.of_datastore_get_import_fields()
        if self.noup_name:
            fields_to_update.remove('name')
        ds_product_ids = [-(ds_product_id + supplier_value) for ds_product_id in ds_product_ids]
        ds_products_data = product_obj.browse(ds_product_ids)._of_read_datastore(fields_to_update, create_mode=True)
        for ds_product_data in itertools.chain(no_match_ids, ds_products_data):
            if isinstance(ds_product_data, (int, long)):
                product = product_obj.browse(ds_product_data)
                ds_product_data = {'active': False}
            else:
                product = id_match.pop(ds_product_data['of_datastore_res_id'])

            # Mise a jour produits actifs/inactifs
            if ds_product_data['active']:
                if product.purchase_ok:
                    # On ne réactive que les articles qui ne peuvent pas être achetés pour éviter de réactiver un article désactivé manuellement
                    del ds_product_data['active']
                else:
                    ds_product_data['purchase_ok'] = True
                    if product.active:
                        del ds_product_data['active']
            else:
                if product.active:
                    if product.purchase_ok:
                        ds_product_data['purchase_ok'] = False
                    if product.virtual_available > 0:
                        del ds_product_data['active']

            ds_product_data = {
                field: val
                for field, val in ds_product_data.iteritems()
                if ((product._fields[field].type != 'many2one' or (val != product[field].id))
                    if product._fields[field].comodel_name
                    else val != product[field])
            }
            if 'uom_id' in ds_product_data:
                # Ligne copiée depuis le module stock dans product.template.write()
                done_moves = self.env['stock.move'].search([('product_id', '=', product.id)], limit=1)
                if done_moves:
                    del ds_product_data['uom_id']
            if ds_product_data:
                product.write(ds_product_data)
        return len(no_match_ids), len(ds_product_ids), len(ds_product_new_ids)

    @api.multi
    def update_products(self):
        self.ensure_one()
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        model_obj = self.env[active_model]

        notes = [""]
        notes_warning = []

        # Preparation de la liste de produits par fournisseur
        datastore_products = {}
        if active_model == 'of.product.brand':
            brands = model_obj.browse(active_ids)
            suppliers = brands.mapped('datastore_supplier_id')
            datastore_products = {supplier: (supplier.brand_ids & brands).mapped('product_variant_ids') for supplier in suppliers}
        elif active_model in ('product.product', 'product.template'):
            to_create = [product_id for product_id in active_ids if product_id < 0]
            if to_create:
                model_obj.browse(to_create).of_datastore_import()
                notes.append(_('Created products : %s') % (len(to_create)))

            to_update = [product_id for product_id in active_ids if product_id > 0]
            products = model_obj.browse(to_update)
            if active_model == 'product.template':
                product_obj = self.env['product.product']
                products = product_obj.with_context(active_test=False).search([('product_tmpl_id', 'in', products._ids)])
                # Retrait du contexte active_test
                products = product_obj.browse(products._ids)
            for product in products:
                supplier = product.of_datastore_supplier_id or False
                if supplier in datastore_products:
                    datastore_products[supplier] += product
                else:
                    datastore_products[supplier] = product

            # Produits sans base fournisseur
            products = datastore_products.pop(False, [])
            if products:
                notes_warning = ["", _('Products the brand of which is not centralized : %s') % len(products)]

        # Recherche des valeurs à mettre à jour
        updt_cnt = 0
        link_cnt = 0
        nolk_cnt = 0
        for supplier, products in datastore_products.iteritems():
            nolk, updt, link = self._update_supplier_products(supplier, products)
            updt_cnt += updt
            link_cnt += link
            nolk_cnt += nolk
        if updt_cnt:
            notes.append(_('Updated products : %s') % (updt_cnt))
        if link_cnt:
            notes.append(_('Added/updated links to centralized products : %s') % (link_cnt))
        if nolk_cnt:
            notes.append(_('Products not updated because not linked : %s') % (nolk_cnt))

        notes[0] = _('Products update ended : %s') % (fields.Datetime().convert_to_display_name(fields.Datetime.now(), self))
        note = "\n".join(notes + notes_warning)

        return self.env['of.popup.wizard'].popup_return(note, titre=_('Import/update notes'))
