# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons.of_datastore_product.models.of_datastore_product import DATASTORE_IND
import time
import itertools
from odoo.exceptions import ValidationError

class OfDatastoreUpdateProduct(models.TransientModel):
    _name = "of.datastore.update.product"
    _description = u"Importer / Mettre à jour les articles"

    def _default_is_update(self):
        active_ids = self._context.get('active_ids') or [0]
        return max(active_ids) > 0

#     u_name = fields.Boolean(string="Nom", default=True)
#     u_code = fields.Boolean(string=u"Référence", default=True)
#     u_tarif = fields.Boolean(string="Tarif", default=True,
#                              help=u"Mise à jour du prix d'achat et répercussion sur le prix de vente selon les règles définies dans le paramétrage")
#     u_uom = fields.Boolean(string=u"Unités de mesure", default=True,
#                            help=u"Mise à jour des unités de mesure utilisées pour les produits.\nLes unités manquantes seront créées au besoin")
#     u_cg = fields.Boolean(string="Conditions d'achat", default=True)
#     u_categ = fields.Boolean(string=u"Catégories de produits")
#     u_kit = fields.Boolean(string="Kits", default=True, help="Met à jour la composition des kits")
#     u_active = fields.Boolean(string="Produit inactif", default=True,
#                               help=u"Désactive les produits retirés par votre fournisseur")
#     remember = fields.Boolean(string=u"Se souvenir de mes préférences",
#                               help=u"Si cette case est cochée, vos préférences seront conservées pour votre prochaine mise à jour avec ce fournisseur")
#     brand_ids = fields.One2many('of.product.brand', compute='_compute_brand_ids', string='Marques')
#     note = fields.Text("Notes")
    is_update = fields.Boolean(u'Afficher les options de mise à jour', default=lambda self: self._default_is_update())

#     @api.depends()
#     def _compute_brand_ids(self):
#         for wizard in self:
#             brands = False
#             model = self._context.get('active_model')
#             if model:
#                 objects = self.env[model].browse(self._context['active_ids'])
#                 if model == 'of.product.brand':
#                     brands = objects
#                 elif model in ('product.product', 'product.template'):
#                     brands = objects.mapped('brand_id')
#             wizard.brand_ids = brands

#     @api.model
#     def default_get(self, fields_list):
#         """
#         Récupère les préférences enregitrées pour le fournisseur
#         """
#         defaults = super(OfDatastoreUpdateProduct, self).default_get(fields_list)
#         model = self._context.get('active_model')
#         if not model:
#             return defaults
#         ds_supplier_id = False
#         objects = self.env[model].browse(self._context['active_ids'])
#         if model == 'of.product.brand':
#             for brand in objects:
#                 if brand.datastore_supplier_id:
#                     ds_supplier_id = brand.datastore_supplier_id.id
#                     break
#         elif model in ('product.product', 'product.template'):
#             for product in objects:
#                 if product.of_datastore_supplier_id:
#                     ds_supplier_id = product.of_datastore_supplier_id.id
#                     break
#         if ds_supplier_id:
#             defaults['ds_supplier_id'] = ds_supplier_id
#             # code repris et modifié de default_get pour intégrer la condition sur le fournisseur
#             ir_values_dict = self.env['ir.values'].get_defaults_dict(self._name, "supplier_%s" % ds_supplier_id)
#             for name in fields_list:
#                 if name in ir_values_dict:
#                     defaults[name] = ir_values_dict[name]
#                     continue
#         return defaults

    def _update_supplier_products(self, supplier, products):
        """
        Met a jour les produits products depuis la base fournisseur supplier
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
                if ds_product_id in id_match:
                    raise ValidationError(_('Two products try to reference the same centralized product : [%s] [%s]') %
                                          (product.default_code, id_match[ds_product_id].default_code))
                id_match[ds_product_id] = product
        ds_product_ids += ds_product_new_ids
#         update_dict = {
#             'u_name': ('name', ),
#             'u_code': ('of_seller_product_code', 'default_code'),
#             'u_tarif': ('list_price', 'standard_price', 'of_seller_pp_ht', 'of_seller_price'),
#             'u_uom': ('uom_id', 'uom_po_id'),
#             'u_cg': ('of_seller_delay', ),
#             'u_categ': ('of_seller_product_category_name', 'categ_id'),
#             'u_kit': ('of_is_kit', 'kit_line_ids', 'of_pricing'),
#             # active est géré à part car on ne réactive pas un article désactivé manuellement
#             'u_active': tuple(),
#             # Les champs à toujours mettre à jour
#             'id': (),
#         }
#         fields_to_update = [field for key,fields in update_dict.iteritems() for field in fields if self[key]]

        # --- Mise à jour des articles ---
        fields_to_update = product_obj.of_datastore_get_import_fields()
        ds_product_ids = [-(ds_product_id + supplier_value) for ds_product_id in ds_product_ids]
        ds_products_data = product_obj.browse(ds_product_ids)._of_read_datastore(fields_to_update, create_mode=True)
        warning_msg = _('This product is no longer available on centralized database')
        for ds_product_data in itertools.chain(no_match_ids, ds_products_data):
            if isinstance(ds_product_data, (int, long)):
                product = product_obj.browse(ds_product_data)
                ds_product_data = {'active': False}
            else:
                product = id_match.pop(ds_product_data['of_datastore_res_id'])

            # Mise a jour produits actifs/inactifs
#             if self.u_active:
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

            if ds_product_data:
                product.write(ds_product_data)
        return len(no_match_ids), len(ds_product_ids), len(ds_product_new_ids)

#     def _update_supplier_products(self, supplier, products):
#         """
#         Met a jour les produits products depuis la base fournisseur supplier
#         @param supplier: browse_record of_datastore_supplier
#         @param products: browse_record_list product.product
#         """
#         product_obj = self.env['product.product']
# 
#         supplier_value = supplier.id * DATASTORE_IND
#         no_match_ids = [product.id for product in products if not product.of_datastore_res_id]
#         id_match = {-(product.of_datastore_res_id + supplier_value): product
#                     for product in products if product.of_datastore_res_id}
# 
#         # Certaines références ont pu être supprimées de la base centrale
#         client = supplier.of_datastore_connect()
#         ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
#         ds_product_ids = [-(ds_product_id + supplier_value) for ds_product_id in id_match]
#         ds_product_ids = supplier.with_context(active_test=False).of_datastore_search(ds_product_obj, [('id', 'in', ds_product_ids)])
#         ds_product_ids = [-(ds_product_id + supplier_value) for ds_product_id in ds_product_ids]
# 
#         no_match_ids += [id_match[ds_product_id].id for ds_product_id in id_match if ds_product_id not in ds_product_ids]            
# 
#         # --- Matching des références avec la base centrale ---
#         # Conversion des références article
#         convert_func = supplier.get_product_code_convert_func()
#         code_to_match_dict = {convert_func[product.brand_id](product.default_code): product
#                               for product in product_obj.browse(no_match_ids)}
#         # Récupération des correspondances de la base centrale
#         ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
#         ds_product_new_ids = supplier.of_datastore_search(ds_product_obj, [('default_code', 'in', code_to_match_dict.keys())])
#         if ds_product_new_ids:
#             for ds_product_data in supplier.of_datastore_read(ds_product_obj, ds_product_new_ids, ['default_code']):
#                 product = code_to_match_dict[ds_product_data['default_code']]
# 
#                 no_match_ids.remove(product.id)
#                 ds_product_id = -(ds_product_data['id'] + supplier_value)
#                 if ds_product_id in id_match:
#                     raise ValidationError(_('Two products try to reference the same centralized product : [%s] [%s]') %
#                                           (product.default_code, id_match[ds_product_id].default_code))
#                 id_match[ds_product_id] = product
#         ds_product_ids += ds_product_new_ids
# #         update_dict = {
# #             'u_name': ('name', ),
# #             'u_code': ('of_seller_product_code', 'default_code'),
# #             'u_tarif': ('list_price', 'standard_price', 'of_seller_pp_ht', 'of_seller_price'),
# #             'u_uom': ('uom_id', 'uom_po_id'),
# #             'u_cg': ('of_seller_delay', ),
# #             'u_categ': ('of_seller_product_category_name', 'categ_id'),
# #             'u_kit': ('of_is_kit', 'kit_line_ids', 'of_pricing'),
# #             # active est géré à part car on ne réactive pas un article désactivé manuellement
# #             'u_active': tuple(),
# #             # Les champs à toujours mettre à jour
# #             'id': (),
# #         }
# #         fields_to_update = [field for key,fields in update_dict.iteritems() for field in fields if self[key]]
# 
#         # --- Mise à jour des articles ---
#         fields_to_update = product_obj.of_datastore_get_import_fields()
#         ds_products_data = product_obj.browse(ds_product_ids + ds_product_new_ids)._of_read_datastore(fields_to_update, create_mode=True)
#         warning_msg = _('This product is no longer available on centralized database')
#         for ds_product_data in itertools.chain(no_match_ids, ds_products_data):
#             if isinstance(ds_product_data, (int, long)):
#                 product = product_obj.browse(ds_product_data)
#                 ds_product_data = {'active': False}
#             else:
#                 product = id_match.pop(ds_product_data['of_datastore_res_id'])
# 
#             # Mise a jour produits actifs/inactifs
# #             if self.u_active:
#             if ds_product_data['active']:
#                 if product.availability == 'warning':
#                     product.availability = 'empty'
#                 else:
#                     # On ne réactive que les articles en disponibilité 'Avertissement' pour éviter de réactiver un article désactivé manuellement
#                     del ds_product_data['active']
#             else:
#                 if product.active:
#                     if product.virtual_available <= 0:
#                         ds_product_data['active'] = False
#                     if product.state != 'warning':
#                         ds_product_data['availability'] = 'warning'
#                         ds_product_data['availability_warning'] = warning_msg
# 
#             if ds_product_data:
#                 product.write(ds_product_data)
#         return len(no_match_ids), len(ds_product_ids), len(ds_product_new_ids)

    @api.multi
    def update_products(self):
        self.ensure_one()
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        model_obj = self.env[active_model]
#        fields_available = ['pa','pv','cg','coeff','categ','act']

        notes = [""]
        notes_warning = []

        # Preparation de la liste de produits par fournisseur
        datastore_products = {}
        if active_model == 'of.product.brand':
            brands = model_obj.browse(active_ids)
            suppliers = brands.mapped('datastore_supplier_id')
            datastore_products = {supplier: supplier.brand_ids.mapped('product_variant_ids') for supplier in suppliers}

#             for brand in brands:
#                 if brand.datastore_supplier_id not in datastore_products:
#                     datastore_products[brand.datastore_supplier_id] = brand.product_variant_ids
#                 else:
#                     datastore_products[brand.datastore_supplier_id] += brand.product_variant_ids
        elif active_model in ('product.product', 'product.template'):
            to_create = [product_id for product_id in active_ids if product_id < 0]
            if to_create:
                model_obj.browse(to_create).of_datastore_import()
                notes.append(u"Produits créés : %s" % (len(to_create)))

            to_update = [product_id for product_id in active_ids if product_id > 0]
            products = model_obj.browse(to_update)
            if active_model == 'product.template':
                products = products.mapped('product_variant_ids')
            for product in products:
                supplier = product.of_datastore_supplier_id or False
                if supplier in datastore_products:
                    datastore_products[supplier] += product
                else:
                    datastore_products[supplier] = product

            # Produits sans base fournisseur
            products = datastore_products.pop(False,[])
            if products:
                notes_warning = ["",u"Produits sans base fournisseur associée : %s" % len(products)]

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
            notes.append(u"Produits mis à jour : %s" % (updt_cnt))
        if link_cnt:
            notes.append(u"Correspondances ajoutées/mises à jour avec la base centrale : %s" % (link_cnt))
        if nolk_cnt:
            notes.append(u"Produits non mis à jour par absence de correspondance : %s" % (nolk_cnt))

#         # Enregistrement des choix
#         if self.remember:
#             value_obj = self.env['ir.values'].sudo()
#             for field in self._fields:
#                 if field.startswith('u_'):
#                     for supplier in datastore_products:
#                         value_obj.set_default(self._name, field, self[field], for_all_users=True, company_id=False,
#                                               condition='supplier_%s' % supplier.id)

        notes[0] = u"Mise à jour des produits terminée à %s" % (time.strftime('%Hh%M:%S'),)
        note = "\n".join(notes + notes_warning)

        return self.env['of.popup.wizard'].popup_return(note, titre=_('Import/update notes'))

        action = self.env.ref('of_datastore_product.action_of_datastore_update_product').read()[0]
        action['res_id'] = self.ids[0]
        return action
