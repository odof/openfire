# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv.expression import NEGATIVE_TERM_OPERATORS, TERM_OPERATORS_NEGATION, TRUE_LEAF, FALSE_LEAF
from odoo.tools.safe_eval import safe_eval

import copy

# 100.000.000 ids devraient suffire pour les produits. Les chiffres suivants serviront pour le fournisseur
DATASTORE_IND = 100000000


def _of_datastore_is_computed_field(model_obj, field_name):
    env = model_obj.env
    field = model_obj._fields[field_name]
    if not field.compute:
        return False
    if field.company_dependent:
        return False
    if not field._description_related:
        return True

    # Traitement particulier des champs related en fonction de la relation
    if model_obj._of_datastore_is_computed_field(field._description_related[0]):
        return True
    f = model_obj._fields[field._description_related[0]]
    for f_name in field._description_related[1:]:
        obj = env[f.comodel_name]
        if not hasattr(obj, '_of_datastore_is_computed_field'):
            # L'objet référencé n'est pas un objet centralisé
            return True
        if obj._of_datastore_is_computed_field(f_name):
            return True
        f = obj._fields[f_name]
    return False


class OfImportProductCategConfig(models.Model):
    _inherit = 'of.import.product.categ.config'

    is_datastore_matched = fields.Boolean('Is centralized')


class OfDatastoreCentralized(models.AbstractModel):
    _name = 'of.datastore.centralized'

    of_datastore_res_id = fields.Integer(string="ID on supplier database", index=True, copy=False)

    @classmethod
    def _browse(cls, ids, env, prefetch=None):
        # Il est important d'hériter de _browse() et non de browse()
        #  car c'est _browse() qui est appelé dans fields.Many2one.convert_to_record()
        result = super(OfDatastoreCentralized, cls)._browse(ids, env, prefetch=prefetch)
        for i in ids:
            if i < 0:
                # Appel de super() pour éviter un appel récursif infini
                record = super(OfDatastoreCentralized, cls)._browse((i, ), env, prefetch=prefetch)
                if not record._cache:
                    env['of.datastore.cache'].apply_values(record)
        return result

    @api.model
    def _get_datastore_unused_fields(self):
        u"""
        Retourne la liste des champs qu'on ne veut pas récupérer chez le fournisseur (par ex. les quantités en stock).
        """
        cr = self._cr

        # On ne veut aucun des champs ajoutés par les modules stock, mrp, purchase
        cr.execute(
            "SELECT f.name "
            "FROM ir_model_data AS d "
            "INNER JOIN ir_model_fields AS f "
            "  ON d.res_id=f.id "
            "WHERE d.model = 'ir.model.fields' "
            "  AND f.model = %s "
            "  AND d.module IN ('mrp','procurement','stock')",
            (self._name, ))
        res = [row[0] for row in cr.fetchall()]

        # Ajout de certains champs
        res += [
            'invoice_policy',
            'purchase_method',

            # Champs à valeur forcée manuellement pour l'import
            'of_import_categ_id',
            'of_import_cout',
            'of_import_price',
            'of_import_remise',

            # Champs de notes
            'description_sale',  # Description pour les devis
            'description_purchase',  # Description pour les fournisseurs
            'description_picking',  # Description pour le ramassage

            # Champs de structure de prix
            'of_purchase_transport',
            'of_sale_transport',
            'of_sale_coeff',
            'of_other_logistic_costs',
            'of_misc_taxes',
            'of_misc_costs',

            # Champs de localisation d'inventaire
            'property_stock_procurement',
            'property_stock_production',
            'property_stock_inventory',
            'of_product_posx',
            'of_product_posy',
            'of_product_posz',
        ]

        # On ne veut pas non-plus les champs one2many ou many2many
        # (seller_ids, packagind_ids, champs liés aux variantes....)
        # On conserve les lignes de kits
        for field_name, field in self._fields.iteritems():
            if field.type in ('one2many', 'many2many'):
                if field_name != 'kit_line_ids' and field_name not in res:
                    res.append(field_name)
        return res

    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        if field_name == 'of_seller_name':
            # Le fournisseur est directement défini par la marque
            return True
        if field_name == 'of_theoretical_cost':
            # Cas particulier pour le coût théorique qu'on veut récupérer du TC
            return False
        return _of_datastore_is_computed_field(self, field_name)

    @api.model
    def _of_get_datastore_computed_fields(self):
        u"""
            Retourne la liste des champs qu'on ne veut pas récupérer chez le fournisseur
            mais qu'il faudra calculer en local (par ex. le champ price qui dépend de la liste de prix du context).
        """
        return [field for field in self._fields if self._of_datastore_is_computed_field(field)]

    @api.multi
    def _of_read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lit les donnees des produits dans leur base fournisseur.
        @param ids: id modifié des produits, en valeur négative
        @param create_mode: En mode create on ne renvoie pas les champs non trouvés (remplis avec False ou [])
                            En mode create on remplit seller_ids
        """
        supplier_obj = self.env['of.datastore.supplier']
        product_tmpl_obj = self.env['product.template']
        result = []

        # Certains champs sont nécessaires pour le calcul d'autres champs :
        # - brand_id : La marque, depuis laquelle on extrait les règles de lecture
        # - categ_id : La catégorie, qui peut correspondre à des règles de lecture plus spécifiques dans la marque
        # - product_tmpl_id : L'article de base, utile pour of_tmpl_datastore_res_id
        # - default_code : La référence de l'article, utile pour of_seller_product_code
        # - uom_id et uom_po_id : Les unités de mesure et de mesure d'achat de l'article,
        #   utiles pour calculer les prix d'achat/vente
        # - list_price : Le prix d'achat de l'article,
        #   à partir duquel sont réalisés les calculs pour le prix de vente et le coût
        # En mode création (create_mode == True), ces champs sont obligatoires donc déjà présents dans fields_to_read.
        # En lecture classique (create_mode == False), nous testons si au moins un champ de fields_to_read
        #   nécessite un accès distant (avec self._get_datastore_unused_fields()).
        #   Si c'est le cas, nous chargeons fields_to_read avec tous les champs de l'objet courant afin de peupler
        #   notre cache et ainsi d'éviter de multiplier les accès distants.
        unused_fields = self._get_datastore_unused_fields() + self._of_get_datastore_computed_fields()
        if not create_mode:
            # Pour la lecture classique, on veut stocker tous les champs en cache pour éviter de futurs accès distants
            for field in fields_to_read:
                if field not in unused_fields:
                    fields_to_read += [field for field in self._fields if field not in fields_to_read]
                    break

        if 'id' in fields_to_read:  # Le champ id sera de toute façon ajouté, le laisser génèrera des erreurs
            fields_to_read.remove('id')

        # Articles par fournisseur
        datastore_product_ids = {}

        # Produits par fournisseur
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_product_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        # Champs a valeurs spécifiques
        fields_defaults = [
            ('of_datastore_supplier_id',        lambda: create_mode and supplier_id or supplier.sudo().name_get()[0]),
            ('of_datastore_res_id',             lambda: vals['id']),
            ('of_seller_pp_ht',                 lambda: vals['of_seller_pp_ht']),
            ('of_seller_product_category_name', lambda: vals['categ_id'][1]),
            ('of_tmpl_datastore_res_id',        lambda: vals['product_tmpl_id'][0]),
            ('description_norme',               lambda: product.description_norme or vals['description_norme']),
            ('of_template_image',               lambda: vals.get('of_template_image') or product.image),
            # Attention, l'ordre des deux lignes suivantes est important
            ('of_seller_product_code',          lambda: vals['default_code']),
            ('default_code',                    lambda: default_code_func[brand](vals['default_code'])),
        ]

        fields_defaults = [(k, v) for k, v in fields_defaults if k in fields_to_read]
        if create_mode:
            # Ajout des champs nécessaires à la creation du product_supplierinfo
            for field in ('of_seller_delay',):
                if field not in fields_to_read:
                    fields_to_read.append(field)

            # Création de la relation fournisseur
            fields_defaults.append(('seller_ids', lambda: [(5, ), (0, 0, {
                'name':    brand.partner_id.id,
                'min_qty': 1,
                'delay':   vals['of_seller_delay'],
            })]))

        datastore_fields = [field for field in fields_to_read if field not in unused_fields]

        m2o_fields = [
            field for field in datastore_fields
            if self._fields[field].type == 'many2one' and
            field != 'of_datastore_supplier_id'
        ]

        o2m_fields = ['kit_line_ids']

        for supplier_id, product_ids in datastore_product_ids.iteritems():
            supplier_value = supplier_id * DATASTORE_IND
            if not datastore_fields:
                if create_mode:
                    result += [{'id': product_id} for product_id in product_ids]
                else:
                    # Pas d'accès à la base centrale, on remplit l'id et on met tout le reste à False ou []
                    datastore_defaults = {
                        field: [] if self._fields[field].type in ('one2many', 'many2many') else False
                        for field in fields_to_read
                        if field != 'id'
                    }
                    result += [
                        dict(datastore_defaults, id=-(product_id + supplier_value))
                        for product_id in product_ids]
                continue
            supplier = supplier_obj.browse(supplier_id)
            client = supplier.of_datastore_connect()
            ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)

            datastore_product_data = supplier_obj.of_datastore_read(
                ds_product_obj, product_ids, datastore_fields, '_classic_read')

            if not create_mode:
                # Les champs manquants dans la table du fournisseur ne sont pas renvoyés, sans générer d'erreur
                # Il faut donc leur attribuer une valeur par défaut
                missing_fields = [field for field in fields_to_read if field not in datastore_product_data[0]]
                # Valeur remplie en 2 étapes
                # 1 : on met une valeur vide (False ou [] pour des one2many)
                datastore_defaults = {
                    field: [] if self._fields[field].type in ('one2many', 'many2many') else False
                    for field in missing_fields
                }
                # 2 : On renseigne les valeurs qui sont trouvées avec la fonction default_get
                datastore_defaults.update(product_tmpl_obj.default_get(missing_fields))

            # Traitement des données
            match_dicts = {}
            match_dicts['brand_id'] = {brand.datastore_brand_id: brand for brand in supplier.brand_ids}

            # Calcul de la fonction à appliquer sur la référence des articles de chaque marque
            if 'default_code' in fields_to_read:
                default_code_func = supplier.get_product_code_convert_func(client)

            datastore_read_m2o_fields = [field for field in m2o_fields if field in datastore_product_data[0]]
            field_res_ids = {field: set() for field in datastore_read_m2o_fields}
            for vals in datastore_product_data:
                # --- Calculs préalables ---
                brand = match_dicts['brand_id'][vals['brand_id'][0]]
                # Ajouter un search par article est couteux.
                # Tant pis pour les règles d'accès, on fait une recherche SQL
                if self._name == 'product.template':
                    self._cr.execute(
                        "SELECT id FROM product_template "
                        "WHERE brand_id = %s AND of_datastore_res_id = %s",
                        (brand.id, vals['id']))
                else:
                    self._cr.execute(
                        "SELECT t.id FROM product_product p "
                        "INNER JOIN product_template t ON t.id=p.product_tmpl_id "
                        "WHERE t.brand_id = %s AND p.of_datastore_res_id = %s",
                        (brand.id, vals['id']))
                rows = self._cr.fetchall()
                product = product_tmpl_obj.browse(rows and rows[0][0])
                categ_name = vals['categ_id'][1]
                obj_dict = {}

                # Calcul des valeurs spécifiques
                for field, val in fields_defaults:
                    vals[field] = val()
                if create_mode:
                    del vals['id']
                else:
                    vals['id'] = -(vals['id'] + supplier_value)
                    vals.update(datastore_defaults)

                # ---- Champs many2one ---
                for field in datastore_read_m2o_fields:
                    # Conversion du many2one pour la base courante
                    if vals[field]:
                        obj = self._fields[field].comodel_name
                        res = brand.datastore_match(
                            client, obj, vals[field][0], vals[field][1], product, match_dicts, create=create_mode)
                        if field in ('categ_id', 'uom_id', 'uom_po_id'):
                            obj_dict[field] = res
                        if res:
                            if res.id < 0:
                                # Valeur de la base centrale
                                # Normalement uniquement utilisé pour product_tmpl_id
                                vals[field] = (res.id, vals[field][1])
                            else:
                                vals[field] = res.id
                                field_res_ids[field].add(res.id)
                        else:
                            vals[field] = False

                # --- Champs x2many ---
                for field in o2m_fields:
                    if field not in datastore_fields:
                        continue
                    if not vals[field]:
                        continue
                    line_ids = [-(line_id + supplier_value) for line_id in vals[field]]
                    if create_mode:
                        # Preparation des lignes
                        obj = self._fields[field].comodel_name
                        obj_obj = self.env[obj]
                        vals[field] = [(5, )] + [(0, 0, line.copy_data()[0]) for line in obj_obj.browse(line_ids)]
                    else:
                        # Conversion en id datastore
                        # Parcours avec indice pour ne pas recreer la liste
                        vals[field] = line_ids

                # --- Champs spéciaux ---
                vals['of_datastore_has_link'] = bool(product)

                # Prix d'achat/vente
                # Note: On retire 'standard_price' de vals car dans certains cas on ne veut pas le mettre à jour
                vals.update(brand.compute_product_price(
                    vals['of_seller_pp_ht'], categ_name, obj_dict['uom_id'], obj_dict['uom_po_id'], product=product,
                    price=vals['of_seller_price'], remise=None, cost=vals.pop('standard_price', None),
                    based_on_price=vals['of_is_net_price']))
                # Calcul de la marge et de la remise
                if 'of_seller_remise' in fields_to_read:
                    vals['of_seller_remise'] =\
                        vals['of_seller_pp_ht'] and\
                        (vals['of_seller_pp_ht'] - vals['of_seller_price']) * 100 / vals['of_seller_pp_ht']
                if 'marge' in fields_to_read:
                    vals['marge'] =\
                        vals['list_price'] and\
                        (vals['list_price'] - vals.get('standard_price', 0)) * 100 / vals['list_price']

                # Suppression des valeurs non voulues
                # Suppression désactivée ... après tout, c'est calculé maintenant, autant le garder en cache
                # for field in added_fields:
                #     vals.pop(field, False)

            if not create_mode:
                # Conversion au format many2one (id,name)
                for field, res_ids in field_res_ids.iteritems():
                    if not res_ids:
                        continue

                    obj = self._fields[field].comodel_name
                    res_obj = self.env[obj].browse(res_ids)
                    res_names = {v[0]: v for v in res_obj.sudo().name_get()}
                    for vals in datastore_product_data:
                        # Test en deux temps car en python, False est une instance de int
                        if vals.get(field) and isinstance(vals[field], (int, long)):
                            vals[field] = res_names[vals[field]]

            result += datastore_product_data
        return result

    def _recompute_check(self, field):
        # Les champs calculés et stockés en base de données doivent toujours être recalculés
        # dans le cas des éléments centralisés.
        result = super(OfDatastoreCentralized, self)._recompute_check(field)
        res1 = self.filtered(lambda record: record.id < 0)
        if result and res1:
            res1 |= result
        # En cas d'ensemble vide, c'est result qui est renvoyé, qui vaut None
        return res1 or result

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        new_ids = [i for i in self._ids if i > 0]

        # Produits sur la base courante
        res = super(OfDatastoreCentralized, self.browse(new_ids)).read(fields, load=load)

        if len(new_ids) != len(self._ids):
            cache_obj = self.env['of.datastore.cache']
            # Si fields est vide, on récupère tous les champs accessibles pour l'objet (copié depuis BaseModel.read())
            self.check_access_rights('read')
            fields = self.check_field_access_rights('read', fields)
            fields = set(fields)
            if 'id' in fields:
                fields.remove('id')
            obj_fields = [self._fields[field] for field in fields]
            use_name_get = (load == '_classic_read')
            # Gestion à part des modèles d'articles, sans quoi of_read_datastore sera appelé pour name_get()
            #   une fois par modèle.
            read_tmpl = self._fields.get('product_tmpl_id') in obj_fields
            tmpl_values = {}

            # Séparation des ids par base centrale
            datastore_product_ids = {}
            for full_id in self._ids:
                if full_id < 0:
                    datastore_product_ids.setdefault(-full_id / DATASTORE_IND, []).append(full_id)

            res = {vals['id']: vals for vals in res}
            for supplier_id, datastore_ids in datastore_product_ids.iteritems():
                with self.env['of.datastore.cache']._get_cache_token(supplier_id) as of_cache:
                    # Vérification des données dans notre cache
                    cached_products = of_cache.search([('model', '=', self._name), ('res_id', 'in', datastore_ids)])

                    # Les articles non en cache sont à lire
                    new_ids = set(datastore_ids) - set(cached_products.mapped('res_id'))

                    # Si au moins un objet est inexistant en cache, tous les champs sont à lire
                    new_fields = set(fields) if new_ids else set()

                    # Les articles dont au moins un champ n'est pas en cache sont aussi à lire, pour au moins ce champ
                    for cached_product in cached_products:
                        product_data = safe_eval(cached_product.vals)
                        missing_fields = fields - set(product_data.keys())
                        if missing_fields:
                            new_fields |= missing_fields
                            new_ids.add(cached_product.res_id)
                        if read_tmpl and 'product_tmpl_id' in product_data:
                            tmpl_values[product_data['product_tmpl_id'][0]] = product_data['product_tmpl_id']

                    if new_ids:
                        # Lecture des données sur la base centrale
                        data = self.browse(new_ids)._of_read_datastore(list(new_fields), create_mode=False)

                        # Stockage des données dans notre cache
                        of_cache.store_values(self._name, data)

                        if read_tmpl and 'product_tmpl_id' in new_fields:
                            for d in data:
                                tmpl_values[d['product_tmpl_id'][0]] = d['product_tmpl_id']

                for obj in self.browse(datastore_ids):
                    # Il faut charger les valeurs dans le cache manuellement car elles ne se chargent de façon
                    #   automatique que si le cache est vide, ce qui n'est plus le cas à ce stade.
                    cache_obj.apply_values(obj)
                    # Filtre des champs à récupérer et conversion au format read
                    vals = {
                        field.name: field.convert_to_read(obj[field.name], self, use_name_get)
                        for field in obj_fields
                    }
                    vals['id'] = obj.id
                    res[obj.id] = vals

                    if read_tmpl:
                        vals['product_tmpl_id'] = tmpl_values[obj.product_tmpl_id.id]

            # Remise des résultats dans le bon ordre
            res = [res[i] for i in self._ids]
        return res

    @api.model
    def of_datastore_update_domain(self, domain):
        u"""
        Vérifie si le domaine indique une recherche sur une base de données fournisseur.
        Si oui, retourne le domaine de recherche adapté pour la base de données fournisseur.
        @requires: Si args contient un tuple dont le premier argument est 'ds_supplier_search_id',
                   le second argument doit être '='
        @return: Id du fournisseur (of.datastore.supplier) ou False sinon, suivi du nouveau domaine de recherche
        """
        if 'of_datastore_product_search' not in domain:
            return False, domain

        domain = [copy.copy(arg) for arg in domain if arg != 'of_datastore_product_search']

        # Recherche des marques
        brand_domain = []
        for arg in domain:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0] == 'brand_id':
                operator, right = arg[1], arg[2]
                # resolve string-based m2o criterion into IDs
                if isinstance(right, basestring) or\
                        right\
                        and isinstance(right, (tuple, list))\
                        and all(isinstance(item, basestring) for item in right):
                    brand_domain.append(('name', operator, right))
                else:
                    brand_domain.append(('id', operator, right))
        brands = self.env['of.product.brand'].search(brand_domain)
        ds_supplier = brands.mapped('datastore_supplier_id')

        if not ds_supplier:
            if brands:
                raise UserError(_('Selected brands are not centralized : %s') % ", ".join(brands.mapped('name')))
            return False, [FALSE_LEAF]

        if len(ds_supplier) > 1:
            raise UserError(_('You must select one or several brands using the same centralized database '
                              '(provided by the same supplier).'))
        brands = brands.filtered('datastore_supplier_id')

        # Recherche des produits non déjà enregistrés
        if self._context.get('datastore_not_stored'):
            orig_ids = self.sudo().with_context(active_test=False)\
                .search([('brand_id', 'in', brands._ids), ('of_datastore_res_id', '!=', False)])\
                .mapped('of_datastore_res_id')
            domain.append(('id', 'not in', orig_ids))

        parse_domain = self._of_datastore_update_domain_item

        # Conversion des champs
        for arg in domain:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0].startswith('ds_'):
                arg[0] = arg[0][3:]
            elif arg[0] in ('categ_id', 'brand_id'):
                obj_name = self._fields[arg[0]].comodel_name
                new_arg = parse_domain(arg, self.env[obj_name])
                if new_arg:
                    arg[0], arg[1], arg[2] = new_arg
        return brands, domain

    @api.model
    def _of_datastore_update_domain_item(self, domain, obj):
        u""" Convertit un élément du domaine pour utilisation sur la base centrale
        @type domain: Tuple (left, operator, right)
        @var obj: Objet sur lequel doit s'appliquer le domaine
        @type obj: Browse record

        @todo: Permettre la conversion de la recherche sur catégories d'articles
        """
        left, operator, right = domain
        if obj._name == 'product.category':
            # Une categorie d'articles peut avoir une correspondance différente selon la marque ou l'article.
            # La conversion est compliquée
            if isinstance(right, basestring) or \
                    right and isinstance(right, (tuple, list)) and all(isinstance(item, basestring) for item in right):
                return False
            else:
                return TRUE_LEAF

        if operator in NEGATIVE_TERM_OPERATORS:
            operator = TERM_OPERATORS_NEGATION[operator]
            new_operator = 'not in'
        else:
            new_operator = 'in'

        if isinstance(right, basestring) or \
                right and isinstance(right, (tuple, list)) and all(isinstance(item, basestring) for item in right):
            obj_domain = [('name', operator, right)]
        else:
            obj_domain = [('id', operator, right)]
        obj = obj.search(obj_domain)

        result = False
        if obj._name == 'of.product.brand':
            result = (left, new_operator, obj.mapped('datastore_brand_id'))
        return result

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        brands, args = self.of_datastore_update_domain(args)

        # Recherche sur la base du fournisseur
        if brands:
            supplier = brands[0].datastore_supplier_id
            # Ex: si la base n'a qu'une base centralisée, elle peut appeler les articles de la base distante
            #     sans autre filtre de recherche.
            # Dans ce cas, on ne veut pas les autres marques du fournisseur
            args = ['&', ('brand_id', 'in', brands.mapped('datastore_brand_id'))] + args

            supplier_obj = self.env['of.datastore.supplier']

            # Exécution de la requête sur la base du fournisseur
            client = supplier.of_datastore_connect()
            if isinstance(client, basestring):
                # Échec de la connexion à la base fournisseur
                raise UserError(u'Erreur accès '+supplier.db_name)

            ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)
            res = supplier_obj.of_datastore_search(ds_product_obj, args, offset, limit, order, count)

            if not count:
                supplier_value = supplier.id * DATASTORE_IND
                res = [-(product_id + supplier_value) for product_id in res]
        else:
            # Éxecution de la requête sur la base courante
            res = super(OfDatastoreCentralized, self)._search(
                args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        return res

    @api.model
    def _of_datastore_name_search(self, res, brands, name, args, operator, limit):
        supplier = brands.mapped('datastore_supplier_id')
        if len(supplier) != 1:
            # Les marques doivent être centralisées, une seule base centrale à la fois
            return res

        if limit != 8 or len(res) == limit:
            # La recherche sur une base fournisseur ne se fait en automatique que pour les recherches
            #   dynamiques des champs many2one (limit=8)
            return res
        if len(res) == 7:
            # Le 8e produit ne sert qu'à savoir si on affiche "Plus de résultats"
            return res + [(False, '')]

        # Recherche des produits dans la base centrale
        client = supplier.of_datastore_connect()
        if isinstance(client, basestring):
            # Échec de la connexion à la base fournisseur
            return res

        brands = brands.filtered('datastore_supplier_id')

        # Recherche des produits non déjà enregistrés
        orig_ids = self.with_context(active_test=False).search(
            [('brand_id', 'in', brands._ids),
             ('of_datastore_res_id', '!=', False)]).mapped('of_datastore_res_id')

        # Mise a jour des paramètres de recherche
        new_args = [('brand_id', 'in', brands.mapped('datastore_brand_id')),
                    ('id', 'not in', orig_ids)] + list(args or [])

        ds_product_obj = supplier.of_datastore_get_model(client, self._name)
        res2 = supplier.of_datastore_name_search(ds_product_obj, name, new_args, operator, limit-len(res))
        supplier_ind = DATASTORE_IND * supplier['id']

        default_code_func = supplier.get_product_code_convert_func(client)
        if len(brands) == 1:
            f = default_code_func[brands]
            res += [[-(pid + supplier_ind), '[' + f(pname[1:]) if pname.startswith('[') else pname]
                    for pid, pname in res2]
        else:
            brand_match = {brand.datastore_brand_id: brand for brand in supplier.brand_ids}
            ds_products_brand = supplier.of_datastore_read(ds_product_obj, zip(*res2)[0], ['brand_id'])
            # {clef=identifiant article sur base centrale : valeur=marque sur base courante}
            ds_products_brand = {data['id']: brand_match[data['brand_id'][0]] for data in ds_products_brand}
            default_code_func = supplier.get_product_code_convert_func(client)
            res += [
                [
                    -(pid + supplier_ind),
                    '[' + default_code_func[ds_products_brand[pid]](pname[1:]) if pname.startswith('[') else pname
                ]
                for pid, pname in res2
            ]
        return res


class Property(models.Model):
    _inherit = 'ir.property'

    @api.model
    def get_multi(self, name, model, ids):
        """ Surcharge pour récupérer une valeur company_dependent d'un article centralisé.
        """
        result = {}
        model_obj = self.env[model]
        if ids and hasattr(model_obj, '_of_read_datastore'):
            ds_ids = [i for i in ids if i < 0]
            if ds_ids:
                ids = [i for i in ids if i >= 0]
                result = {d['id']: d[name] for d in model_obj.browse(ds_ids)._of_read_datastore([name])}
        result.update(super(Property, self).get_multi(name, model, ids))
        return result
