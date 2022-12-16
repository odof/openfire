# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from of_datastore_product import DATASTORE_IND


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    datastore_supplier_id = fields.Many2one('of.datastore.supplier', string='Centralized products connector')
    datastore_brand_id = fields.Integer(string='Centralized ID')

    datastore_note_maj = fields.Text(string='Update notes', compute='_compute_datastore_note_maj')
    datastore_product_count = fields.Integer(
        string='# Products', compute='_compute_datastore_note_maj',
        help="The number of products of this brand")

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        if self._context.get('of_datastore_update_categ') and fields and 'categ_ids' in fields:
            self = self.with_context(of_datastore_update_categ=False, no_clear_datastore_cache=True)
            categ_ids = {name: categ_id for categ_id, name in self.env['product.category'].search([]).name_get()}
            categ_obj = self.env['of.import.product.categ.config']
            try:
                categ_obj.check_access_rights('create')
                categ_obj.check_access_rights('write')

                supplier_clients = {}
                # Récupération dans supplier_categs des correspondances deja renseignées

                for brand in self:
                    supplier = brand.datastore_supplier_id
                    if not supplier:
                        brand.categ_ids.filtered('is_datastore_matched').write({'is_datastore_matched': False})
                        brand.categ_all_ids = brand.categ_ids
                        continue

                    if supplier not in supplier_clients:
                        supplier_clients[supplier] = supplier.of_datastore_connect()
                    client = supplier_clients[supplier]

                    if isinstance(client, basestring):
                        # Echec de la connexion à la base fournisseur
                        brand.categ_ids.filtered('is_datastore_matched').write({'is_datastore_matched': False})
                        brand.categ_all_ids = brand.categ_ids
                        brand.datastore_note_maj = 'Error\n' + client
                        continue

                    stored_categs = {categ.categ_origin: categ for categ in brand.categ_ids}

                    # Récupération des catégories de produits de la base du fournisseur
                    # On ne prend que les catégories contenant au moins 1 article de la marque
                    ds_product_obj = supplier.of_datastore_get_model(client, 'product.template')
                    ds_products_vals = supplier.with_context(active_test=False).of_datastore_read_group(
                        ds_product_obj, [('brand_id', '=', brand.datastore_brand_id)], ['categ_id'],
                        'categ_id', offset=None, limit=None, orderby=None, lazy=None)

                    categs = categ_obj.browse()
                    for ds_product in ds_products_vals:
                        categ_origin = ds_product['categ_id'][1]
                        stored_categ = stored_categs.pop(categ_origin, False)
                        if stored_categ:
                            if not stored_categ.is_datastore_matched:
                                stored_categ.is_datastore_matched = True
                            categs += stored_categ
                        else:
                            categs += categ_obj.create({
                                'brand_id': brand.id,
                                'of_import_categ_id': categ_ids.get(categ_origin, False),
                                'categ_origin': categ_origin,
                                'is_datastore_matched': True,
                            })
                    for categ in stored_categs.itervalues():
                        if categ.of_import_price or categ.of_import_remise or categ.of_import_cout\
                                or categ.of_import_categ_id:
                            # Une configuration a été saisie, on la garde par sentimentalité
                            if categ.is_datastore_matched:
                                categ.is_datastore_matched = False
                            categs += categ
                        else:
                            categ.unlink()

                    brand.categ_ids = categs
            except Exception:
                pass
        return super(OfProductBrand, self).read(fields, load=load)

    @api.depends('datastore_supplier_id')
    def _compute_datastore_note_maj(self):
        suppliers_brands = {}

        # Regroupement des marques par base centrale
        for brand in self:
            if brand.datastore_supplier_id:
                suppliers_brands.setdefault(brand.datastore_supplier_id, []).append(brand.datastore_brand_id)

        suppliers_data = {}
        for supplier, brand_ids in suppliers_brands.iteritems():
            client = supplier.of_datastore_connect()
            if isinstance(client, basestring):
                suppliers_data[supplier] = u"Échec de la connexion à la base centrale\n\n" + client
                continue
            ds_brand_obj = supplier.of_datastore_get_model(client, 'of.product.brand')
            ds_brand_ids = supplier.of_datastore_search(ds_brand_obj, [('id', 'in', brand_ids)])
            suppliers_data[supplier] = {
                data['id']: (data['note_maj'], data['product_count'])
                for data in supplier.of_datastore_read(ds_brand_obj, ds_brand_ids, ['note_maj', 'product_count'])
            }

        for brand in self:
            product_count = 0
            if not brand.datastore_supplier_id:
                note = u"Marque non associée à une base centrale"
            elif isinstance(suppliers_data[brand.datastore_supplier_id], basestring):
                note = suppliers_data[brand.datastore_supplier_id]
            elif brand.datastore_brand_id not in suppliers_data[brand.datastore_supplier_id]:
                note = u"Marque non présente sur la base centrale"
            else:
                note, product_count = suppliers_data[brand.datastore_supplier_id][brand.datastore_brand_id]
            brand.datastore_note_maj = note
            brand.datastore_product_count = product_count

    @api.multi
    def datastore_match(self, client, obj, res_id, res_name, product, match_dicts, create=True):
        """ Tente d'associer un objet de la base centrale à un id de la base de l'utilisateur
        @param client: client connecté à la base du fournisseur
        @param obj: nom de l'objet à faire correspondre
        @param res_id: id de l'instance de l'objet à faire correspondre
        @param match_dicts: dictionnaire des correspondances par objet
        @return: Entier correspondant a l'id de l'object correspondant dans la base courante, ou False
        """
        def datastore_matching_model(obj_name, obj_id):
            """ Teste si une correspondance existe dans la table ir_model_data
            @warning: Cette façon de faire est dangereuse car les éléments ont pu être modifiés à la main,
                      ne l'utiliser que pour de rares modèles.
            """
            model_ids = ds_supplier_obj.of_datastore_search(
                ds_model_obj, [('model', '=', obj_name), ('res_id', '=', obj_id)])
            if not model_ids:
                return self.env[obj_name]
            model = ds_supplier_obj.of_datastore_read(ds_model_obj, model_ids, ['module', 'name'])[0]
            res_id = model_obj.search([('module', '=', model['module']), ('name', '=', model['name'])]).res_id
            # Dans certains cas, un objet a pu être supprimé en DB mais pas sa référence dans ir_model_data
            return self.env[obj_name].search([('id', '=', res_id)])
        # --- Gestion des cas particuliers ---
        if obj == self._name:
            return self
        if obj == 'product.category':
            return self.compute_product_categ(res_name, product)

        match_dict = match_dicts.setdefault(obj, {})

        # Recherche de correspondance dans les valeurs précalculées
        if res_id in match_dict:
            return match_dict[res_id]

        # Recherche de correspondance dans les identifiants externes (ir_model_data)
        model_obj = self.env['ir.model.data']
        ds_supplier_obj = self.env['of.datastore.supplier']
        ds_model_obj = ds_supplier_obj.of_datastore_get_model(client, 'ir.model.data')
        ds_obj_obj = ds_supplier_obj.of_datastore_get_model(client, obj)
        result = False

        # Calcul de correspondance en fonction de l'objet
        obj_obj = self.env[obj]
        if obj == 'product.template':
            if product:
                result = product
            else:
                # Ajouter un search par article est couteux.
                # Tant pis pour les règles d'accès, on fait une recherche SQL
                self._cr.execute(
                    "SELECT id FROM product_template WHERE brand_id = %s AND of_datastore_res_id = %s",
                    (self.id, res_id))
                result = self._cr.fetchall()
                if result:
                    result = obj_obj.browse(result[0][0])
                else:
                    if create:
                        result = False
                    else:
                        # product_tmpl_id ne doit pas etre False,
                        # notamment a cause de la fonction pricelist.price_get_multi qui genererait une erreur
                        # Pour eviter des effets de bord, on met une valeur negative
                        result = obj_obj.browse(-(res_id + self.datastore_supplier_id.id * DATASTORE_IND))
        elif obj == 'product.uom.categ':
            result = datastore_matching_model(obj, res_id)
            if not result:
                result = obj_obj.search([('name', '=', res_name)], limit=1)
                if not result:
                    raise ValidationError(u"Catégorie d'UDM inexistante : " + res_name)
        elif obj == 'product.uom':
            # Etape 1 : Déterminer la catégorie d'udm
            ds_obj = ds_supplier_obj.of_datastore_read(
                ds_obj_obj, [res_id], ['category_id', 'factor', 'uom_type', 'rounding'])[0]

            categ = self.datastore_match(
                client, 'product.uom.categ', ds_obj['category_id'][0], ds_obj['category_id'][1], product, match_dicts)

            # Etape 2 : Vérifier si l'unité de mesure existe
            uoms = obj_obj.search(
                [('factor', '=', ds_obj['factor']),
                 ('uom_type', '=', ds_obj['uom_type']),
                 ('category_id', '=', categ.id)])

            if uoms:
                if len(uoms) > 1:
                    # Ajout d'un filtre sur le nom pour préciser la recherche
                    uoms = obj_obj.search([('id', 'in', uoms.ids), ('name', '=ilike', res_name)]) or uoms
                if len(uoms) > 1:
                    # Tentative de matching par xml_id
                    uoms = uoms & datastore_matching_model(obj, res_id) or uoms
                if len(uoms) > 1:
                    # Ajout d'un filtre sur le nom pour préciser la recherche : même préfixe sur 4 lettres
                    uoms = obj_obj.search([('id', 'in', uoms.ids), ('name', '=ilike', res_name[:4]+'%')]) or uoms
                if len(uoms) > 1:
                    # Ajout d'un filtre sur la précision de l'arrondi pour préciser la recherche
                    uoms = obj_obj.search([('id', 'in', uoms.ids), ('rounding', '=', ds_obj['rounding'])]) or uoms
                result = uoms[0]
            elif create:
                # Etape 3 : Créer l'unité de mesure
                uom_data = {
                    'name':        res_name,
                    'uom_type':    ds_obj['uom_type'],
                    'factor':      ds_obj['factor'],
                    'category_id': categ.id,
                    'rounding':    ds_obj['rounding'],
                }
                result = obj_obj.create(uom_data)
        else:
            if obj_obj._rec_name:
                result = obj_obj.search([(obj_obj._rec_name, '=', res_name)])
                if len(result) != 1:
                    result = False
        match_dict[res_id] = result
        return result

    @api.multi
    def clear_datastore_cache(self):
        """ Fonction de nettoyage du cache.
        Le cache étant un TransientModel, il est automatiquement nettoyé tous les jours
        La fonction _transient_vacuum() d'Odoo efface tous les TransientModel dont le write_date ou create_date
          est vieux de plus d'une heure
         - Tous les jours, via le cron base.autovacuum_job
         - Tous les 20 appels de _create()
        Cette fonction de nettoyage permet un nettoyage manuel supplémentaire par base centrale.
        Le but est de pouvoir nettoyer par connecteur TC si besoin, notamment lorsque les règles
          de calcul ont été modifiées dans la marque.
        """
        suppliers = self.mapped('datastore_supplier_id')
        domain = [('model', 'in', ('product.product', 'product.template'))] + ['|'] * (len(suppliers._ids) - 1)
        for supplier in suppliers:
            domain += [
                '&',
                ('res_id', '<=', -DATASTORE_IND * supplier.id),
                ('res_id', '>', -DATASTORE_IND * (supplier.id + 1))
            ]
        self.env['of.datastore.cache'].search(domain).unlink()

    def _datastore_update_product_vals(self, product_vals):
        """
        Importe les articles centralisés utilisés dans product_vals.
        :param product_vals: Liste de règles x2many.
        :return: product_vals mis à jour avec les ids des articles après import.
        """
        vals = []
        new_products = self.env['product.template']
        for val in product_vals:
            if val[0] == 6:
                pass
            elif val[1] < 0:
                product = self.env['product.template'].browse(val[1]).of_datastore_import()
                val = [v for v in val]
                val[1] = product.id
                new_products |= product
            vals.append(val)
        return vals, new_products

    @api.multi
    def write(self, vals):
        # Autorise l'ajout de règles pour des articles centralisés
        new_products = False
        if vals.get('product_config_ids', False):
            vals['product_config_ids'], new_products = self._datastore_update_product_vals(vals['product_config_ids'])

        res = super(OfProductBrand, self).write(vals)

        # Lors de la modification de la marque, les données en cache sont invalidées
        if vals and self and not self._context.get('no_clear_datastore_cache'):
            self.clear_datastore_cache()
        if new_products:
            new_products.of_action_update_from_brand()
        return res
