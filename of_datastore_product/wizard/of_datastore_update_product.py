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
    # Ajout du field type pour permettre l'import de tous les articles depuis la marque
    type = fields.Selection([('update', 'Update'), ('import', 'Import')], string="Type", default="update")

    def _update_links(self, supplier, client, product_ids, id_match):
        """
        Matching des références avec la base centrale
        Cette fonction lie les articles (product.product) au TC si une référence correspond.
        Les articles correctement liés sont alors retirés de la liste product_ids et ajoutés au dictionnaire id_match.
        @param supplier: browse_record of_datastore_supplier
        @param client: informations connecteur TC
        @param product_ids: liste d'ids des articles qui ne sont liés à un article du TC
        @param id_match: dictionnaire d'ids TC et leurs correpondances sur la base
        @return: Liste des ids des articles de la base centrale correctement liés
        """
        product_obj = self.env['product.product']
        ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
        # --- Matching des références avec la base centrale ---
        # Conversion des références article
        convert_func = supplier.get_product_code_convert_func()
        code_to_match_dict = {convert_func[product.brand_id](product.default_code): product
                              for product in product_obj.browse(product_ids)}
        # Récupération des correspondances de la base centrale
        ds_product_new_ids = supplier.of_datastore_search(ds_product_obj, [('default_code', 'in', code_to_match_dict.keys())])
        if ds_product_new_ids:
            for ds_product_data in supplier.of_datastore_read(ds_product_obj, ds_product_new_ids, ['default_code']):
                product = code_to_match_dict[ds_product_data['default_code']]

                product_ids.remove(product.id)
                if ds_product_data['id'] in id_match:
                    raise ValidationError(_('Two products try to reference the same centralized product : [%s] [%s]') %
                                          (product.default_code, id_match[ds_product_data['id']].default_code))
                product.of_datastore_res_id = ds_product_data['id']
                id_match[ds_product_data['id']] = product
        return ds_product_new_ids

    def _update_supplier_products(self, supplier, products):
        """
        Met à jour les produits products depuis la base fournisseur supplier
        @param supplier: browse_record of_datastore_supplier
        @param products: browse_record_list product.product
        """
        product_obj = self.env['product.product']
        product_template_obj = self.env['product.template']

        supplier_value = supplier.id * DATASTORE_IND
        # Détection des articles non liés à la base centrale.
        no_match_ids = [product.id for product in products if not product.of_datastore_res_id]
        id_match = {product.of_datastore_res_id: product
                    for product in products if product.of_datastore_res_id}

        # Certaines références ont pu être supprimées de la base centrale
        client = supplier.of_datastore_connect()
        ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
        ds_product_ids = supplier.with_context(active_test=False).of_datastore_search(ds_product_obj, [('id', 'in', id_match.keys())])

        # Articles dont le lien existait mais dont la cible n'existe plus
        unmatched_ids = [id_match[ds_product_id].id for ds_product_id in id_match if ds_product_id not in ds_product_ids]
        no_match_ids += unmatched_ids

        ds_product_new_ids = self._update_links(supplier, client, no_match_ids, id_match)
        ds_product_ids += ds_product_new_ids

        # Les articles dont le lien existait et a été brisé doivent être désactivés.
        # En revanche les articles qui n'étaient déjà pas liés ne doivent pas subir de mise à jour.
        unmatched_ids = [i for i in unmatched_ids if i in no_match_ids]

        # --- Mise à jour des articles ---
        products_write_data = {}
        fields_to_update = product_obj.of_datastore_get_import_fields()
        if self.noup_name:
            fields_to_update.remove('name')
        ds_product_ids = [-(ds_product_id + supplier_value) for ds_product_id in ds_product_ids]
        ds_products_data = product_obj.browse(ds_product_ids)._of_read_datastore(fields_to_update, create_mode=True)

        for ds_product_data in itertools.chain(unmatched_ids, ds_products_data):
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

            if ds_product_data.get('seller_ids'):
                # La fonction _of_read_datastore renvoie un seller_ids de la forme [(5, ), (0, 0, {...})]
                # Cela pose un problème de performance, car le (5, ) appelle la fonction unlink(), qui vide toutes les valeurs en cache
                # On retire donc le code (5, ) et on remplace au besoin le (0, ) par un (1, )
                old_sellers = ds_product_data['seller_ids']
                sellers = ds_product_data['seller_ids'] = []
                for seller in old_sellers:
                    if seller[0] == 5:
                        continue
                    if seller[0] == 0:
                        if not product.seller_ids:
                            sellers.append(seller)
                        elif len(product.seller_ids) == 1:
                            sellers.append((1, product.seller_ids.id, seller[2]))
                        else:
                            supplier_id = seller[2]['name']
                            for old_seller in product.seller_ids:
                                if old_seller.name.id == supplier_id:
                                    # Edition du fournisseur correspondant
                                    sellers.append((1, old_seller.id, seller[2]))
                                    break
                            else:
                                # Plusieurs fournisseurs sans possibilité de choisir... on en crée un autre !
                                sellers.append(seller)
                    else:
                        raise ValidationError("Mise à jour de tarif : type de renvoi de fournisseur non prévu\ncode: %s" % (old_sellers, ))
            if ds_product_data:
                # L'appel write() est reporté après tous les calculs.
                # En effet, write() vide certaines données en cache
                #   (les données qui sont compute =True et store=False, e.g. of_datastore_has_link, of_seller_price, etc.)
                # Lorsqu'Odoo recalcule ces données, il le fait, à chaque itération, sur la totalité des articles (ds_product_ids),
                #   ce qui provoque un temps de calcul en O(n²) au lieu de O(n)
                products_write_data[product] = ds_product_data
        for product, product_data in products_write_data.iteritems():
            product.write(product_data)

        # Mise à jour du paramètre active des product.template
        # Activation
        product_template_obj.search([('active', '=', False), ('product_variant_ids.active', '=', True)]).write({'active': True})
        # Désactivation des modèles d'articles qui n'ont pas au moins un article (variante) actif.
        active_templates = product_template_obj.search([('active', '=', True)])
        active_product_templates = product_obj.search([('active', '=', True)]).mapped('product_tmpl_id')
        (active_templates - active_product_templates).write({'active': False})

        return len(no_match_ids), len(unmatched_ids), len(ds_product_ids), len(ds_product_new_ids)

    @api.multi
    def update_products(self):
        """
        Fonction qui permet de mettre à jour ou importer les produits de la base TC
        vers la base client
        """
        self.ensure_one()
        product_obj = self.env['product.product']
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        model_obj = self.env[active_model]

        notes = [""]
        notes_warning = []
        to_create = []

        # Preparation de la liste de produits par fournisseur
        datastore_products = {}
        if active_model == 'of.product.brand':
            brands = model_obj.browse(active_ids)
            suppliers = brands.mapped('datastore_supplier_id')
            datastore_products = {
                # Récupération de tous les articles même inactifs de la marque.
                # On appelle product_obj.browse pour conserver le context d'origine et éviter des recalculs de cache.
                supplier: product_obj.browse((supplier.brand_ids & brands)
                                             .with_context(active_test=False)
                                             .mapped('product_variant_ids')._ids)
                for supplier in suppliers}

        elif active_model in ('product.product', 'product.template'):
            model_obj.search('')
            to_create = set([product_id for product_id in active_ids if product_id < 0])
            to_update = [product_id for product_id in active_ids if product_id > 0]

            if to_create:
                # Détection des articles déjà importés
                create_product_ids = {}
                for full_id in to_create:
                    supplier_id = -full_id / DATASTORE_IND
                    create_product_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)
                for supplier_id, product_ids in create_product_ids.iteritems():
                    supplier_ind = DATASTORE_IND * supplier_id
                    existing = model_obj.with_context(active_test=False).search(
                        [('brand_id.datastore_supplier_id', '=', supplier_id),
                         ('of_datastore_res_id', 'in', product_ids)])
                    to_update += existing._ids
                    to_create -= set(-(product.of_datastore_res_id + supplier_ind) for product in existing)

            products = model_obj.browse(to_update)
            if active_model == 'product.template':
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

        #  Mise à jour des produits/ajout des liens TC avant de créer les nouveaux produits sur base client
        updt_cnt = link_cnt = unlk_cnt = nolk_cnt = 0
        for supplier, products in datastore_products.iteritems():
            nolk, unlk, updt, link = self._update_supplier_products(supplier, products)
            updt_cnt += updt
            link_cnt += link
            unlk_cnt += unlk
            nolk_cnt += nolk

        #  Import de tous les produits non liés de la marque
        if active_model == 'of.product.brand' and self.type == 'import':
            model_obj = self.env['product.product']
            unwanted_ids = []
            for brand in brands:
                unwanted_ids += model_obj.search([('brand_id', '=', brand.id),
                                                  ('of_datastore_res_id', '!=', False)]).mapped('of_datastore_res_id')

            for brand in brands:
                supplier = brand.datastore_supplier_id
                supplier_value = supplier.id * DATASTORE_IND
                client = supplier.of_datastore_connect()
                ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
                ds_product_ids = supplier.of_datastore_search(ds_product_obj, [('brand_id', '=', brand.datastore_brand_id), ('id', 'not in', unwanted_ids)])
                ds_product_ids = [-(ds_product_id + supplier_value) for ds_product_id in ds_product_ids]
                to_create += ds_product_ids

        if to_create:
            model_obj.browse(to_create).of_datastore_import()
            notes.append(_('Created products : %s') % (len(to_create)))

        # Recherche des valeurs à mettre à jour

        if updt_cnt:
            notes.append(_('Updated products : %s') % (updt_cnt))
        if link_cnt:
            notes.append(_('Added/updated links to centralized products : %s') % (link_cnt))
        if unlk_cnt:
            notes.append(_('Products removed from centralized database : %s') % (unlk_cnt))
        if nolk_cnt:
            notes.append(_('Products not updated because not linked : %s') % (nolk_cnt))

        notes[0] = _('Products update ended : %s') % (fields.Datetime().convert_to_display_name(fields.Datetime.now(), self))
        note = "\n".join(notes + notes_warning)

        return self.env['of.popup.wizard'].popup_return(note, titre=_('Import/update notes'))
