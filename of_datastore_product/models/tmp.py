# -*- coding: utf-8 -*-
import copy

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

DATASTORE_IND = 100000000 # 100.000.000 ids devraient suffire pour les produits. Les chiffres suivants serviront pour le fournisseur

"""
NOTES
=====

Matching des catégories de produits
-----------------------------------
Les catégories de produits proposées ne devraient être que celles effectivement utilisées (au moins un article actif)
Par extension, un article inactif côté fournisseur ne devrait jamais être affiché côté distributeur

Les paramètres de connexion serveur doivent être gérés dans un objet caché, disponible uniquement pour le compte administrateur.
Cela règle le problème de l'export de données donnant accès à l'identifiant et au mot de passe de la base fournisseur (sauf manipulation des droits)
"""

#@todo: Matching des comptes comptables, taxes, kits

# Table permettant de faire correspondre un fournisseur à une base de données
# Pour la recherche de produits, il va falloir un id
class OfDatastoreSupplier(models.Model):
    _name = 'of.datastore.supplier'
    _inherit = 'of.datastore.connector'
    _description = u"Correspondance entre une marque et une base de données"
    _rec_name = 'db_name'
    _order="name"

    brand_ids = fields.One2many('of.product.brand', 'datastore_supplier_id', string='Allowed brands')
#    partner_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier', '=', True)], required=True)
#    partner_id = fields.One2many('res.partner', 'of_datastore_supplier_id', string='Supplier', domain=[('supplier', '=', True)], required=True)
#    name = fields.Char(related='db_name', string='Name')

    new_password = fields.Char(string='Set Password',
        compute='_compute_password', inverse='_inverse_password',
        help="Specify a value only when changing the password, otherwise leave empty")
    error_msg = fields.Char(string='Error', compute='_compute_categ_ids')
#     maj_note = fields.Text(string='Notes MAJ', compute='_compute_categ_ids')
    product_ids = fields.One2many('product.product', 'datastore_supplier_id', string='Products')

    active = fields.Boolean('Active', default=True)


    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u'Une connexion à cette base existe déjà')
    ]

    @api.depends()
    def _compute_password(self):
        for supplier in self:
            supplier.password = ''

    # Fonctions récupérées depuis le champ new_password défini pour res_users.
    def _inverse_password(self):
        for supplier in self:
            if not supplier.new_password:
                # Do not update the password if no value is provided, ignore silently.
                # For example web client submits False values for all empty fields.
                continue
            supplier.password = supplier.new_password

#     @api.multi
#     @api.depends()
#     def _compute_categ_ids(self):
#         if not self:
#             return {}
# 
#         supplier_clients = self.of_datastore_connect()
#         try:
#             # Récupération dans supplier_categs des correspondances deja renseignées
# 
#             for supplier in self:
#                 client = supplier_clients[supplier.id]
# 
#                 if isinstance(client, basestring):
#                     #Echec de la connexion à la base fournisseur
#                     supplier.categ_ids = [categ.id for categ in supplier.stored_categs]
#                     supplier.error_msg = client
#                     supplier.maj_note = ''
#                     continue
#                 stored_categs = {categ.orig_id: categ for categ in supplier.stored_categs}
# 
#                 # Récupération des catégories de produits de la base du fournisseur
#                 ds_categ_obj = self.of_datastore_get_model(client, 'product.category')
#                 ds_categ_ids = self.of_datastore_search([])
#                 data = {}
#                 for orig_id, orig_name in self.of_datastore_name_get(ds_categ_obj, ds_categ_ids):
#                     stored_categ = stored_categs.get(orig_id)
#                     if stored_categ:
#                         if stored_categ.orig_name == orig_name:
#                             line_data = (4, stored_categ.id)
#                         else:
#                             line_data = (1, stored_categ.id, {'orig_name': orig_name})
#                     else:
#                         line_data = (0, 0, {'supplier_id': supplier.id,
#                                             'orig_id'    : orig_id,
#                                             'orig_name'  : orig_name})
#                     data[orig_id] = line_data
# 
#                 # On peut éventuellement ajouter un code 2 pour chaque ligne de stored_categs non présente dans data
#                 # (categorie supprimée côté fournisseur)
# 
#                 # Récupération des notes de mise à jour
#                 ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
#                 ds_brand_ids = self.of_datastore_search(ds_brand_obj, [('prefix', 'in', supplier.brand_ids.mapped('prefix'))])
#                 brand_notes = {brand['prefix']: brand['note']
#                                for brand in self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['prefix', 'note'])}
# 
#                 brand_notes = []
#                 for brand in supplier.brand_ids:
#                     brand_note = brand_notes.get(brand.prefix, '').strip()
#                     if brand_note:
#                         brand_notes.append("%s\n%s" % (brand.name, brand_note))
# 
#                 supplier.categ_ids = [data[i] for i in ds_categ_ids]  # Mise des catégories dans l'ordre défini par ds_categ_ids
#                 supplier.error_msg = u"Connexion réussie"
#                 supplier.maj_note = "\n\n".join("notes")
#         finally:
#             self.of_datastore_free_connection(supplier_clients)
# 
#     def _inverse_categ_ids(self):
#         for supplier in self:
#             supplier.stored_categs = supplier.categ_ids




    @api.onchange('server_address')
    def onchange_server_address(self):
        if self.server_address and not self.server_address.startswith('http'):
            return {'value': {'server_address': 'https://' + self.server_address}}
        return False

    @api.onchange('db_name')
    def onchange_db_name(self):
        if self.db_name:
            return {'value': {'server_address': 'https://' + self.db_name + '.openfire.fr'}}
        return False

    @api.multi
    def datastore_match(self, client, obj, res_id, match_dicts, create=True):
        """ Tente d'associer un objet de la base centrale à un id de la base de l'utilisateur
        @param client: client openerplib connecté à la base du fournisseur
        @param obj: nom de l'objet à faire correspondre
        @param res_id: id de l'instance de l'objet à faire correspondre
        @param match_dicts: dictionnaire des correspondances par objet
        @return: Entier correspondant a l'id de l'object correspondant dans la base courante, ou False
        """
        def datastore_matching_model(obj_name, obj_id):
            """ Teste si une correspondance existe dans la table ir_model_data
            """
            model_ids = self.of_datastore_search(ds_model_obj, [('model', '=', obj_name), ('res_id', '=', obj_id)], context=self._context or {})
            if not model_ids:
                return False
            model = self.of_datastore_read(ds_model_obj, model_ids[0], ['module', 'name'], self._context)

            res_id = model_obj.get_object_reference(model['module'], model['name'])
            # Dans certains cas, un objet a pu être supprimé en DB mais pas sa référence dans ir_model_data
            if res_id and not self.env[obj_name].search([('id', '=', res_id)]):
                res_id = False
            return res_id
        self.ensure_one()
        match_dict = match_dicts.setdefault(obj, {})

        # Recherche de correspondance dans les valeurs précalculées
        if res_id in match_dict:
            return match_dict[res_id]

        # Recherche de correspondance dans les identifiants Odoo (ir_model_data)
        model_obj = self.pool['ir.model.data']
        ds_model_obj = self.of_datastore_get_model(client, 'ir.model.data')
        ds_obj_obj = self.of_datastore_get_model(client, obj)
        result = False

        # Calcul de correspondance en fonction de l'objet
        obj_obj = self.env[obj]
        if obj == 'product.category':
            result = self.with_context({}).get_matching_categ(client, [res_id], match_dicts={})[res_id]
        elif obj == 'product.uom.categ':
            result = datastore_matching_model(obj, res_id)
            if not result:
                ds_obj = self.of_datastore_read(ds_obj_obj, res_id, ['name'])
                result = obj_obj.search([('name', '=', ds_obj['name'])], limit=1)
                if not result:
                    raise UserError(u"Catégorie d'UDM inexistante : " + ds_obj.name)
        elif obj == 'product.uom':
            # Etape 1 : Déterminer la catégorie d'udm
            ds_obj = self.of_datastore_read(ds_obj_obj, res_id, ['category_id', 'factor', 'uom_type', 'name', 'rounding'])

            categ_id = self.datastore_match(client, 'product.uom.categ', ds_obj['category_id'][0],
                                            match_dicts, context=self._context)

            # Etape 2 : Vérifier si l'unité de mesure existe
            uoms = obj_obj.search([('factor', '=', ds_obj['factor']),
                                   ('uom_type', '=', ds_obj['uom_type']),
                                   ('category_id', '=', categ_id)])

            if uoms:
                if len(uoms) > 1:
                    # Ajout d'un filtre sur le nom pour préciser la recherche
                    uoms = obj_obj.search([('id', 'in', uoms._ids), ('name', '=ilike', ds_obj['name'])]) or uoms
                if len(uoms) > 1:
                    # Ajout d'un filtre sur la précision de l'arrondi pour préciser la recherche
                    uom_ids = obj_obj.search([('id', 'in', uoms._ids),('rounding', '=', ds_obj['rounding'])]) or uoms
                result = uom_ids[0]
            elif create:
                # Etape 3 : Creer l'unite de mesure
                uom_data = {
                    'name'       : ds_obj['name'],
                    'uom_type'   : ds_obj['uom_type'],
                    'factor'     : ds_obj['factor'],
                    'category_id': categ_id,
                    'rounding'   : ds_obj['rounding'],
                }
                result = obj_obj.create(uom_data)
        match_dict[res_id] = result
        return result





    @api.multi
    def get_matching_categ(self, client, categ_ids, match_dicts={}):
        """
        Met à jour match_dicts avec les correspondances de catégories calculées.
        Retourne les valeurs correspondant à categ_ids
        """
        if not categ_ids:
            return {}
        self.ensure_one()

        # Dictionnaire de correspondances {catégorie_fournisseur : catégorie_base_courante}
        if not match_dicts.get('product.category'):
            match_dicts['product.category'] = {categ.orig_id: categ.categ_id.id for categ in self.stored_categs if categ.categ_id}
        matches = match_dicts['product.category']

        # Dictionnaire des valeurs non renseignées {catégorie_fournisseur_inconnue : catégories_fournisseur_dépendantes (filles)}
        unmatched = {categ_id: [categ_id] for categ_id in categ_ids if categ_id not in matches}

        if unmatched:
            ds_categ_obj = self.of_datastore_get_model(client, 'product.category')

            while unmatched:
                categs = self.of_datastore_read(ds_categ_obj, unmatched.keys(), ['parent_id'], self._context)
                new_unmatched = {}
                for categ in categs:
                    categ_id = categ['id']
                    parent_id = categ['parent_id']
                    if not parent_id:
                        # Une correspondance est manquante, on génère une erreur avec le nom de la catégorie non répertoriée
                        for cid in unmatched[categ_id]:
                            if cid in categ_ids:
                                cname = self.of_datastore_name_get(ds_categ_obj, [cid], self._context)[0][1]
                                raise UserError(u'Une correspondance est manquante dans les catégories de produits du fournisseur : %s' % (cname,))

                    if parent_id in matches:
                        match = matches[parent_id]
                        for cid in unmatched[categ_id]:
                            matches[cid] = match
                    elif parent_id in new_unmatched:
                        new_unmatched[parent_id] += unmatched[categ_id]
                    else:
                        new_unmatched[parent_id] = [parent_id] + unmatched[categ_id]
                unmatched = new_unmatched
        return {key: val for key,val in matches.iteritems() if key in categ_ids}

    @api.multi
    def get_matching_remise(self, client, categ_ids, match_dicts={}, field="remise"):
        u"""
        Met à jour match_dicts avec les liens catégorie - remise calculés.
        Retourne les valeurs correspondant à categ_ids
        @param field: remise ou price_ttc
        """
        if not categ_ids:
            return {}
        self.ensure_one()

        key = "product.product_"+field
        supplier_remise = getattr(self, field)

        # Dictionnaire de correspondances {categorie_fournisseur : remise}
        if not match_dicts.get(key):
            match_dicts[key] = {categ.orig_id: getattr(categ, field) or supplier_remise
                                for categ in self.stored_categs
                                if getattr(categ, field)}
        matches = match_dicts[key]

        unmatched = [categ_id for categ_id in categ_ids if categ_id not in matches]

        if unmatched:
            ds_categ_obj = self.of_datastore_get_model(client, 'product.category')
            categs = ds_categ_obj.read(ds_categ_obj.search([]), ['parent_id'])
            parent = {categ['id']: categ['parent_id'] and categ['parent_id'][0] for categ in categs}

            for categ_id in unmatched:
                if categ_id in matches:
                    continue
                to_fill = [categ_id]
                remise = supplier_remise
                while True:
                    categ_id = parent[categ_id]
                    if categ_id:
                        if categ_id in matches:
                            remise = matches[categ_id]
                            break
                        else:
                            to_fill.append(categ_id)
                    else:
                        break
                for categ_id in to_fill:
                    matches[categ_id] = remise
        return {key:val for key,val in matches.iteritems() if key in categ_ids}

    @api.model
    def compute_remise(self, *remises):
        result = 100
        for remise in remises:
            result *= (100 - remise) / 100.0
        return 100 - result

    @api.model
    def button_dummy(self):
        return True


# class OfDatastoreProductCategory(models.Model):
#     _name = "of.datastore.product.category"
#     _description = "Correspondance entre catégories de produits"
# 
#     supplier_id = fields.Many2one('of.datastore.supplier', required=True, ondelete='cascade')
#     orig_name = fields.Char(string=u'Catégorie fournisseur', required=True)
#     orig_id = fields.Integer(string='Identifiant fournisseur', required=True)
#     categ_id = fields.Many2one('product.category', string=u'Catégorie')
#     remise = fields.Char(string='Remise', help=u"""Remise à appliquer sur les articles de cette catégorie
# 
# Exemples:
#  rc : Utiliser la remise conseillée
#  40 : Forcer une remise de 40%
#  cumul(rc,10,5) : Appliquer la remise conseillée, puis un remise de 10%, puis une remise de 5%
#  cumul(rc,14.5) : Equivalent à la ligne précedente, une remise de 10% puis 5% fait 14.5% au total
# """)
#     price_ttc = fields.Char(string='Prix de vente', help=u"""Modification à appliquer sur le prix de vente conseillé.
# 
# Exemples : 
#  pv : Conserve le prix de vente conseillé
#  pv * 1.05 + tf * 0.4 : Augmente le prix de vente de 5%, plus 40% des transports et frais""")
# 
#     _order = 'orig_name'

# class ResPartner(models.Model):
#     _inherit = 'res.partner'
# 
#     of_datastore_supplier_id = fields.Many2one('of.datastore.supplier', string="Connexion tarif centralisé")


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    datastore_supplier_id = fields.Many2one

    categ_ids = fields.One2many('of.import.product.categ.config', 'brand_id', string="Catégories")
    all_categ_ids = fields.One2many(
        'of.import.product.categ.config', compute="_compute_all_categ_ids", inverse="_inverse_all_categ_ids", string="Catégories")

    @api.multi
    @api.depends()
    def _compute_all_categ_ids(self):
        if not self:
            return {}

        supplier = self.datastore_supplier_id
        supplier_clients = supplier.of_datastore_connect()
        # Récupération dans supplier_categs des correspondances deja renseignées

        for brand in self:
            supplier = brand.supplier_id
            client = supplier_clients[brand.supplier_id.id]

            if isinstance(client, basestring):
                # Echec de la connexion à la base fournisseur
                brand.all_categ_ids = [categ.id for categ in brand.categ_ids]
                supplier.error_msg = client
                supplier.maj_note = ''
                continue
            stored_categs = {categ.orig_id: categ for categ in brand.categ_ids}

            # Récupération des catégories de produits de la base du fournisseur
            ds_categ_obj = supplier.of_datastore_get_model(client, 'product.category')
            ds_categ_ids = supplier.of_datastore_search(ds_categ_obj, [])
            data = {}
            for orig_id, orig_name in self.of_datastore_name_get(ds_categ_obj, ds_categ_ids):
                stored_categ = stored_categs.get(orig_id)
                if stored_categ:
                    if stored_categ.orig_name == orig_name:
                        line_data = (4, stored_categ.id)
                    else:
                        line_data = (1, stored_categ.id, {'orig_name': orig_name})
                else:
                    line_data = (0, 0, {'supplier_id': supplier.id,
                                        'orig_id'    : orig_id,
                                        'orig_name'  : orig_name})
                data[orig_id] = line_data

            # On peut éventuellement ajouter un code 2 pour chaque ligne de stored_categs non présente dans data
            # (categorie supprimée côté fournisseur)

            # Récupération des notes de mise à jour
            ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
            ds_brand_ids = self.of_datastore_search(ds_brand_obj, [('prefix', 'in', supplier.brand_ids.mapped('prefix'))])
            brand_notes = {brand['prefix']: brand['note']
                           for brand in self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['prefix', 'note'])}

            brand_notes = []
            for brand in supplier.brand_ids:
                brand_note = brand_notes.get(brand.prefix, '').strip()
                if brand_note:
                    brand_notes.append("%s\n%s" % (brand.name, brand_note))

            supplier.categ_ids = [data[i] for i in ds_categ_ids]  # Mise des catégories dans l'ordre défini par ds_categ_ids
            supplier.error_msg = u"Connexion réussie"
            supplier.maj_note = "\n\n".join("notes")

    def _inverse_categ_ids(self):
        for supplier in self:
            supplier.stored_categs = supplier.categ_ids

    @api.multi
    def link_products(self, product_ids=False, log=False):
        u"""
        Détecte et renseigne les liens entre des produits existants et d'éventuels homologues dans
          les bases fournisseurs (utilise le prefixe renseigné dans le of_datastore_suplier)
        Les produits représentent de gros volumes de données.
        On utilise donc surtout des requêtes SQL plutôt que des appels odoo standards
        @param self: fournisseurs potentiels, vide pour chercher parmi tous les fournisseurs
        @param product_ids: id des produits potentiels, False pour chercher pour tous les produits non renseignés
        Au moins un des champs self ou product_ids doit contenir des éléments
        """
        datastore_product_ids = {}

        # Detection des produits à chercher par base fournisseur
        if self:
            request = "SELECT id,default_code FROM product_product WHERE default_code LIKE %s AND (datastore_product_id IS NULL OR datastore_product_id = 0)"
            if product_ids:
                request += " AND id IN (%s)" % (",".join([str(i) for i in product_ids]), )
            for supplier in self:
                self._cr.execute(request, (supplier.product_prefix + "\\_%", ))
                datastore_product_ids[supplier.id] = dict(self._cr.fetchall())
        elif product_ids:
            # Selection de la partie du code produit qui se trouve avant la premiere occurence du caractere '_'
            self._cr.execute("SELECT id,default_code,substring(default_code from E'^(.*?)\_') "
                             "FROM product_product "
                             "WHERE id IN %s AND (datastore_product_id IS NULL OR datastore_product_id = 0)" ,
                             (tuple(product_ids), ))
            ds_product_ids = {}
            for product_id, default_code, prefix in self._cr.fetchall():
                ds_product_ids.setdefault(prefix, {})[product_id] = default_code
            for prefix, product_data in ds_product_ids.iteritems():
                supplier_ids = self.search([('product_prefix', '=', prefix)])
                for supplier_id in supplier_ids:
                    datastore_product_ids[supplier_id] = product_data
        else:
            return False

        query = "UPDATE product_product SET datastore_product_id=%s, datastore_supplier_id=%s WHERE id=%s"
        log_data = []
        for supplier in self.browse(datastore_product_ids.keys()):
            supplier_id = supplier.id
            product_data = datastore_product_ids[supplier_id]
            client_dict = supplier.connect()
            try:
                ds_product_obj = self.of_datastore_get_model(client_dict[supplier_id], 'product.product')
                ds_product_ids = self.of_datastore_search(ds_product_obj, [('default_code', 'in', product_data.values())])
                ds_products = self.of_datastore_read(ds_product_obj, ds_product_ids, ['default_code'])
                ds_products = {p['default_code']: p['id'] for p in ds_products}

                for product_id, code in product_data.iteritems():
                    res_id = ds_products.get(code)
                    if res_id:
                        self._cr.execute(query % (res_id, supplier_id, product_id))
                log_data.append((supplier, len(ds_product_ids)))
            finally:
                self.of_datastore_free_connection(client_dict)
        if log:
            for supplier, nb_updt in log_data:
                supplier.log(u"%s produits existants ont été associés au founisseur %s" % (nb_updt, supplier.name))
        return {}

    @api.multi
    def action_link_products(self):
        self.link_products(product_ids=False, log=True)
        return True




class OfDatastoreCentralized(models.AbstractModel):
    _name = 'of.datastore.centralized'

    datastore_res_id = fields.Integer(string="Identifiant base fournisseur")

    @api.model
    def _get_datastore_unused_fields(self):
        return []

    @api.multi
    def _read_datastore(self, fields_to_read, create_mode=False):
        return []

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        new_ids = [i for i in self._ids if i>0]
        datastore_ids = [i for i in self._ids if i<0]

        # Produits sur la base courante
        res = super(OfDatastoreCentralized, self.browse(new_ids)).read(fields, load=load)
        
        if datastore_ids:
            # Si fields est vide, on récupère tous les champs accessibles pour l'objet (copié depuis BaseModel.read())
            fields = self.check_field_access_rights('read', fields)
            res += self.browse(datastore_ids)._read_datastore(fields, create_mode=False)
        return res




    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super(OfDatastoreCentralized, self).name_search(name=name, args=args, operator=operator, limit=limit)
        if limit != 8 or len(res) == limit:
            # La recherche sur une base fournisseur ne se fait en automatique que pour les recherches
            #   dynamiques des champs many2one (limit=8)
            return res
        if len(res) == 7:
            # Le 8e produit ne sert qu'à savoir si on affiche "Plus de résultats"
            return res + [False]
        ds_supplier_obj = self.env['of.datastore.supplier']
        brand_obj = self.env['of.product.brand']

        # Récupération des préfixes trouvés dans name
        name_list = name.split()
        prefixes = [s.split('_', 1)[0].upper().lstrip('[') for s in name_list]

        ds_suppliers = ds_supplier_obj.browse()
        supplier_brands = {}
        for brand in brand_obj.search([('prefix', 'in', prefixes)]):
            ds_suppliers |= brand.supplier_id
            if brand.supplier_id in supplier_brands:
                supplier_brands[brand.supplier_id] |= brand
            else:
                supplier_brands[brand.supplier_id] = brand

        if not ds_suppliers:
            return res

        clients = ds_supplier_obj.of_datastore_connect()
        try:
            for supplier in ds_suppliers:
                if len(res) == limit:
                    break

                client = clients[supplier.id]
                if isinstance(client, basestring):
                    # Échec de la connexion à la base fournisseur
                    continue

                brands = supplier_brands[supplier]

                # Recherche des produits non déjà enregistrés
                self._cr.execute('SELECT datastore_product_id '
                                 'FROM %s '
                                 'WHERE brand_id IN %%s'
                                 ' AND datastore_product_id IS NOT NULL' % (self._table), (tuple(brands.mapped('prefix')), ))
                orig_ids = [row[0] for row in self._cr.fetchall()]

                # Mise à jour des paramètres de recherche
                prefixes = brands.mapped('prefix')
                long_prefixes = sum([[p, p+'_', p+'\\_'] for p in prefixes], [])
                new_name = " ".join([s for s in name_list if s.upper() not in long_prefixes])
                new_args = [('brand_id.prefix', 'in', prefixes),
                            ('id', 'not in', orig_ids)
                           ] + args

                ds_product_obj = self.of_datastore_get_model(client, 'product.product')
                res2 = self.of_datastore_name_search(ds_product_obj, new_name, new_args, operator, limit-len(res))
                supplier_ind = DATASTORE_IND * supplier.id
                res += [[-(pid+supplier_ind), pname] for pid, pname in res2]
        finally:
            ds_supplier_obj.free_connection(clients)

        return res





class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['product.template', 'of.datastore.centralized']




class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ['product.product', 'of.datastore.centralized']

#     datastore_product_id = fields.Integer(u'Identifiant base fournisseur', index=True)
    datastore_supplier_id = fields.Many2one('of.datastore.supplier', string="Centralisation fournisseur", index=True,
        help=u"Fournisseur permettant la mise à jour de ce produit grâce à la centralisation OpenFire des tarifs")
    # Champ dummy permettant de faire des recherches sur une base fournisseur spécifique
    ds_supplier_search_id = fields.One2many('of.datastore.supplier', related='datastore_supplier_id', string="Recherche sur base fournisseur")

#     def __init__(self, pool, cr):
#         # Récupération de tous les préfixes des codes de produits actifs présents en base de données
#         cr.execute("SELECT DISTINCT substring(default_code FROM E'.*?_') FROM product_product WHERE active")
#         self._product_prefixes = [row[0][:-1].upper() for row in cr.fetchall() if row[0]]
#         return super(ProductProduct,self).__init__(pool,cr)

    datastore_product_id = fields.Integer(u'Identifiant base fournisseur', index=True)
    datastore_supplier_id = fields.Many2one('of.datastore.supplier', string="Centralisation fournisseur", index=True,
        help=u"Fournisseur permettant la mise à jour de ce produit grâce à la centralisation OpenFire des tarifs")
    # Champ dummy permettant de faire des recherches sur une base fournisseur spécifique
    ds_supplier_search_id = fields.One2many('of.datastore.supplier', related='datastore_supplier_id', string="Recherche sur base fournisseur")

    @api.model
    def datastore_update_domain(self, domain):
        """
        Vérifie si le domaine indique une recherche sur une base de données fournisseur.
        Si oui, retourne le domaine de recherche adapté pour la base de données fournisseur.
        @requires: Si args contient un tuple dont le premier argument est 'ds_supplier_search_id', le second argument doit être '='
        @return: Id du fournisseur (of.datastore.supplier) ou False sinon, suivi du nouveau domaine de recherche
        """
        supplier_id = False

        # Duplication du domaine
        domain = copy.deepcopy(domain)
        # Détection de l'utilisation d'une base de fournisseur
        for arg in domain:
            if isinstance(arg, (list, tuple)) and arg[0] == 'ds_supplier_search_id':
                supplier_id = arg[2]
                prefix = self.env['of.datastore.supplier'].browse(supplier_id).product_prefix
                # Le distributeur ne peut voir que les articles de la marque configurée pour ce fournisseur
                arg[0] = 'default_code'
                arg[1] = '=like'
                arg[2] = prefix + '\\_%'
                break
        if not supplier_id:
            # Pas de base fournisseur specifiée, recherche sur la base actuelle
            return False, domain

        # Recherche des produits non deja enregistres
        if not self._context.get('datastore_stored'):
            self._cr.execute('SELECT datastore_product_id '
                             'FROM product_product '
                             'WHERE datastore_supplier_id=%s AND datastore_product_id IS NOT NULL',
                             (supplier_id, ))
            orig_ids = [row[0] for row in self._cr.fetchall()]
            domain.append(('id', 'not in', orig_ids))

        # Conversion des catégories de produits
        for arg in domain:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0].startswith('ds_'):
                arg[0] = arg[0][3:]
            elif arg[0] == 'categ_id':
                if arg[1] == 'child_of':
                    pass # @todo: Voir comment integrer ça joliment
                else:
                    categ_ids = arg[2]
                    if arg[1] == '=':
                        arg[1] = 'in'
                        categ_ids = [categ_ids]
                    elif arg[1] in ('!=','<>'):
                        arg[1] = 'not in'
                        categ_ids = [categ_ids]
                    self._cr.execute('SELECT DISTINCT orig_id '
                                     'FROM of_datastore_product_category '
                                     'WHERE supplier_id=%s AND categ_id IN %s', (supplier_id, tuple(categ_ids)))
                    arg[2] = [row[0] for row in self._cr.fetchall()]
        return supplier_id, domain

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        supplier_id, args = self.datastore_update_domain(args)

        # Recherche sur la base du fournisseur
        if supplier_id:
            supplier_obj = self.env['of.datastore.supplier']

            # Exécution de la requête sur la base du fournisseur
            client = supplier_obj.browse(supplier_id).of_datastore_connect()[supplier_id]
            if isinstance(client, basestring):
                # Échec de la connexion à la base fournisseur
                supplier_name = supplier_obj.browse(supplier_id).name
                raise UserError(u'Erreur accès '+supplier_name, client)

            try:
                ds_product_obj = self.of_datastore_get_model(client, 'product.product')
                res = self.of_datastore_search(ds_product_obj, args, offset, limit, order, count, self._context)
            finally:
                supplier_obj.of_datastore_free_connection({supplier_id: client})

            if not count:
                supplier_value = supplier_id * DATASTORE_IND
                res = [-(product_id + supplier_value) for product_id in res]
        else:
            # Éxecution de la requête sur la base courante
            res = super(ProductProduct, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        return res

    @api.model
    def _get_datastore_unused_fields(self):
        # Champs qu'on ne veut pas récupérer chez le fournisseur (quantités en stock)

        # On ne veut aucun des champs ajoutés par les modules stock, mrp, purchase
        self._cr.execute("SELECT f.name "
                         "FROM ir_model_data AS d "
                         "INNER JOIN ir_model_fields AS f "
                         "  ON d.res_id=f.id "
                         "WHERE d.model = 'ir.model.fields' "
                         "  AND f.model IN ('product.product','product.template') "
                         "  AND d.module IN ('mrp','procurement','stock'); ")
        res = [row[0] for row in self._cr.fetchall()]

        # Ajout de certains champs du module product
        res += [
            'incoming_qty',
            'outgoing_qty',
            'qty_available',
            'virtual_available',
            'supply_method',
        ]

        # On ne veut pas non-plus les champs one2many ou many2many (normalement limité a 'seller_ids' et 'packaging'
        # Utilisation de _all_columns pour récupérer les colonnes de product_template également
        # On conserve les lignes de kits
        for field_name,field in self._all_columns.iteritems():
            if field.column._type in ('one2many','many2many'):
                if field_name != 'kit_lines' and field_name not in res:
                    res.append(field_name)
        return res

    @api.multi
    def _read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lit les données des produits dans leur base fournisseur.
        @param ids: id modifié des produits, en valeur négative
        @param create_mode: En mode create on ne renvoie pas les champs non trouvés (remplis avec False ou [])
                            En mode create on remplit seller_ids
        """
        supplier_obj = self.env['of.datastore.supplier']
        product_supplierinfo_obj = self.env['product.supplierinfo']
        margin_prec = self._columns['price_margin'].digits[1]
        res = []

        fields_to_read.pop('id', False) # Le champ id sera de toute façon ajouté, le laisser génèrera des erreurs

        # Produits par fournisseur
        datastore_product_ids = {}
        for i in self._ids:
            supplier_id = -i / DATASTORE_IND
            datastore_product_ids.setdefault(supplier_id, []).append((-i) % DATASTORE_IND)

        suppliers = supplier_obj.browse(datastore_product_ids.keys())
        clients = suppliers.of_datastore_connect()
        try:
            # Champs a valeurs specifiques
            fields_defaults = {
                'datastore_supplier_id': lambda:supplier_m2o_id,
                'datastore_product_id' : lambda:vals['id'],

                'list_price'           : lambda:standard_price,
#                'standard_price'       : lambda:standard_price,
                'price_margin'         : lambda:price_margin,
#                'list_pvht'            : lambda:list_pvht,
#                'lst_price_ttc'        : lambda:list_pvht * (1.0 + (self._get_tva('lst_price_ttc') or 0.2)),
#                'lst_price_ttc2'       : lambda:list_pvht * (1.0 + (self._get_tva('lst_price_ttc2') or 0.055)),
#                'lst_price_ttc3'       : lambda:list_pvht * (1.0 + (self._get_tva('lst_price_ttc3') or 0.1)),
#                'price_remise'         : lambda:remise,
#                'coef'                 : lambda:price_margin * 1.2,
            }

            fields_defaults = {k:v for k,v in fields_defaults.iteritems() if k in fields_to_read}
            if create_mode:
                # Création de la relation fournisseur
                fields_defaults['seller_ids'] = lambda:[(0, 0, product_supplierinfo_obj.read([]))]

            datastore_fields = [field for field in fields_to_read if field not in self._get_datastore_unused_fields() + fields_defaults.keys()]

            m2o_fields = [field for field in datastore_fields
                          if self._all_columns[field].column._type  == 'many2one'
                          and field != 'datastore_supplier_id']

            o2m_fields = ['kit_lines'] # :-)

            # Ajout de champs nécessaires au calcul du prix de vente
            # La conversion de categ_id n'est pas nécessaire dans ce cas, donc on ne l'ajoute pas à m2o_fields
            added_fields = [field for field in ('categ_id', 'standard_price', 'price_remise', 'price_extra', 'list_pvht')
                            if field not in datastore_fields]
            datastore_fields += added_fields

            for supplier_id, product_ids in datastore_product_ids.iteritems():
                supplier = supplier_obj.browse(supplier_id)
                client = clients[supplier_id]
                ds_product_obj = self.of_datastore_get_model(client, 'product.product')

                if datastore_fields:
                    datastore_product_data = self.of_datastore_read(ds_product_obj, product_ids, datastore_fields, '_classic_read')
                else:
                    # Si il n'y a plus aucun field, ds_product_obj.read lirait TOUS les field disponibles, ce qui aurait l'effet inverse (et génèrerait des erreurs de droits)
                    datastore_product_data = [{'id': product_id} for product_id in product_ids]
                supplier_value = supplier_id * DATASTORE_IND

                if not create_mode:
                    # Les champs manquants dans la table du fournisseur ne sont pas renvoyés, sans générer d'erreur
                    # Il faut donc leur attribuer une valeur par défaut (False ou [] pour des One2many)
                    # Utilisation de _all_columns pour récupérer les colonnes de product_template également
                    datastore_defaults = {field: [] if self._all_columns[field].column._type in ('one2many', 'many2many') else False
                                          for field in fields_to_read if field not in datastore_product_data[0]}

                # Traitement des données
                match_dicts = {}

                # Équation de calcul de la remise
                for vals in datastore_product_data:
                    ds_categ_id = vals['categ_id'][0]
                    for field in ('remise', 'price_ttc'):
                        vals[field + '_eval'] = supplier.get_matching_remise(client, [ds_categ_id], match_dicts=match_dicts, field=field)[ds_categ_id]

                # Conversion des champs many2one
                for field in m2o_fields:
                    if field not in datastore_product_data[0]:
                        continue
                    if field == 'product_tmpl_id':
                        # product_tmpl_id ne doit pas être False, notamment à cause de la fonction pricelist.price_get_multi qui génèrerait une erreur
                        # Pour éviter des effets de bord, on met une valeur négative
                        for vals in datastore_product_data:
                            if vals[field]:
                                if create_mode:
                                    vals[field] = -vals[field][0]
                                else:
                                    vals[field][0] *= -1
                        continue

                    # Conversion du many2one pour la base courante
                    obj = self._all_columns[field].column._obj
                    res_ids = []
                    for vals in datastore_product_data:
                        if vals[field]:
                            res_id = supplier.datastore_match(client, obj, vals[field][0], match_dicts, create=create_mode)
                            vals[field] = res_id
                            if res_id and res_id not in res_ids: res_ids.append(res_id)

                    if not create_mode:
                        # Conversion au format many2one (id, name)
                        obj_obj = self.env[obj].sudo()
                        res_names = {v[0]:v for v in obj_obj.name_get(res_ids)}
                        for vals in datastore_product_data:
                            if vals[field]:
                                vals[field] = res_names[vals[field]]

                # Conversion des champs one2many/many2many
                for field in o2m_fields:
                    if field not in datastore_fields:
                        continue
                    for vals in datastore_product_data:
                        if not vals[field]:
                            continue
                        line_ids = [-(line_id + supplier_value) for line_id in vals[field]]
                        if create_mode:
                            # Preparation des lignes
                            obj = self._all_columns[field].column._obj
                            obj_obj = self.env[obj]
                            vals[field] = [(0, 0, obj_obj.copy_data(line_id)) for line_id in line_ids]
                        else:
                            # Conversion en id datastore
                            # Parcours avec indice pour ne pas recréer la liste
                            vals[field] = line_ids

                # Champs particuliers
                supplier_m2o_id = supplier_id if create_mode else supplier.name_get()[0]
                for vals in datastore_product_data:
                    # Préparation des variables
                    price_remise   = vals['price_remise']
                    standard_price = vals['standard_price']
                    price_extra    = vals['price_extra']
                    list_pvht      = vals['list_pvht']
                    for field in added_fields:
                        del vals[field]

                    eval_dict = {
                        'rc'   : price_remise,
                        'ra'   : price_remise,
                        'cumul': supplier_obj.compute_remise,
                    }

                    # Calcul de la remise sur prix d'achat
                    remise_eval = vals.pop('remise_eval')
                    remise = safe_eval(remise_eval, eval_dict)
                    if remise != price_remise:
                        if remise >= 100:
                            standard_price = 0.0
                        else:
                            standard_price *= (100-remise)/(100.0-price_remise)

                    # Calcul prix de vente modifiés
                    eval_dict.update({
                        'r'  : remise,
                        'pv' : price_extra + standard_price * 100 / (100.0 - remise) if remise < 100 else list_pvht,
                        'tf' : price_extra,
                    })
                    price_eval = vals.pop('price_ttc_eval')
                    list_pvht = safe_eval(price_eval, eval_dict)
                    price_margin = standard_price and round((list_pvht - price_extra) / standard_price, margin_prec) or 1
                    remise = 100 - 100.0 / price_margin

                    # Calcul des valeurs specifiques
                    for field, val in fields_defaults.iteritems():
                        vals[field] = val()
                    if create_mode:
                        del vals['id']
                    else:
                        vals['id'] = -(vals['id'] + supplier_value)
                        vals.update(datastore_defaults)
                res += datastore_product_data
        finally:
            supplier_obj.free_connection(clients)
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        supplier_id, ds_domain = self.datastore_update_domain(domain)

        # Recherche sur la base du fournisseur
        if supplier_id:
            supplier_obj = self.env['of.datastore.supplier']
            supplier = supplier_obj.browse(supplier_id)

            # Exécution de la requête sur la base du fournisseur
            client_dict = supplier.of_datastore_connect()
            try:
                ds_product_obj = self.of_datastore_get_model(client_dict[supplier_id], 'product.product')
                res = self.of_datastore_read_group(ds_product_obj, ds_domain, fields, groupby, offset, limit, orderby, lazy, self._context)
            finally:
                supplier_obj.of_datastore_free_connection(client_dict)

            if groupby:
                # Affectation du domaine sur les différentes lignes
                for d in res:
                    d_domain = d['__domain'][0]
                    d_domain[0] = 'ds_' + d_domain[0]
                    d['__domain'] = [d_domain] + domain
        else:
            # Exécution de la requête sur la base courante
            res = super(ProductProduct, self).read_group(domain, fields, groupby, offset=offset, limit=None, orderby=orderby, lazy=lazy)
        return res

    @api.multi
    def copy(self, default=None):
        default = default or {}
        default.update({
            'datastore_product_id' : False,
            'datastore_supplier_id': False,
        })
        return super(ProductProduct, self).copy(default)

    @api.multi
    def write(self, vals):
        for i in self._ids:
            if i < 0:
                raise UserError(u"Vous ne pouvez pas modifier un article directement sur la base centrale du fournisseur.\n"
                                u"Veuillez l'importer au préalable.\n"
                                u"Si l'article est déjà importé, vous pouvez y accéder en vidant le champ de recherche \"Recherche sur base fournisseur\".")
        return super(ProductProduct, self).write(vals)

    @api.multi
    def datastore_import(self):
        if len(self._ids) == 1:
            # Détection de l'existence du produit
            # Ce cas peut se produire dans un object de type commande, si plusieurs lignes ont la même référence
            # Ou encore dans un inventaire, à chaque nouvelle ligne saisie
            ds_supplier_id = -self._ids[0] / DATASTORE_IND
            ds_product_id = (-self._ids[0]) % DATASTORE_IND
            result = self.search([('datastore_supplier_id', '=', ds_supplier_id), ('datastore_product_id', '=', ds_product_id)])
            if result:
                return result[0]

        fields_to_read = [f for f,c in self._all_columns.iteritems()
                          if getattr(c.column, '_classic_write')
                          and not c.column.compute
                          and f != 'product_tmpl_id']
        fields_to_read.append('kit_lines')

        result = []
        for product_data in self._read_datastore(fields_to_read, create_mode=True):
            result.append(self.create(product_data))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super(ProductProduct, self).name_search(name=name, args=args, operator=operator, limit=limit)
        if limit != 8 or len(res) == limit:
            # La recherche sur une base fournisseur ne se fait en automatique que pour les recherches
            #   dynamiques des champs many2one (limit=8)
            return res
        if len(res) == 7:
            # Le 8e produit ne sert qu'à savoir si on affiche "Plus de résultats"
            return res + [False]
        ds_supplier_obj = self.env['of.datastore.supplier']
        brand_obj = self.env['of.product.brand']

        # Récupération des préfixes trouvés dans name
        name_list = name.split()
        prefixes = [s.split('_', 1)[0].upper().lstrip('[') for s in name_list]

        ds_suppliers = ds_supplier_obj.browse()
        supplier_brands = {}
        for brand in brand_obj.search([('prefix', 'in', prefixes)]):
            ds_suppliers |= brand.supplier_id
            if brand.supplier_id in supplier_brands:
                supplier_brands[brand.supplier_id] |= brand
            else:
                supplier_brands[brand.supplier_id] = brand

        if not ds_suppliers:
            return res

        clients = ds_supplier_obj.of_datastore_connect()
        try:
            for supplier in ds_suppliers:
                if len(res) == limit:
                    break

                client = clients[supplier.id]
                if isinstance(client, basestring):
                    # Échec de la connexion à la base fournisseur
                    continue

                brands = supplier_brands[supplier]

                # Recherche des produits non déjà enregistrés
                self._cr.execute('SELECT datastore_product_id '
                                 'FROM product_product '
                                 'WHERE brand_id IN %s'
                                 ' AND datastore_product_id IS NOT NULL', (tuple(brands.mapped('prefix')), ))
                orig_ids = [row[0] for row in self._cr.fetchall()]

                # Mise à jour des paramètres de recherche
                prefixes = brands.mapped('prefix')
                long_prefixes = sum([[p, p+'_', p+'\\_'] for p in prefixes], [])
                new_name = " ".join([s for s in name_list if s.upper() not in long_prefixes])
                new_args = [('brand_id.prefix', 'in', prefixes),
                            ('id', 'not in', orig_ids)
                           ] + args

                ds_product_obj = self.of_datastore_get_model(client, 'product.product')
                res2 = self.of_datastore_name_search(ds_product_obj, new_name, new_args, operator, limit-len(res))
                supplier_ind = DATASTORE_IND * supplier.id
                res += [[-(pid+supplier_ind), pname] for pid, pname in res2]
        finally:
            ds_supplier_obj.free_connection(clients)

        return res

    @api.multi
    def assign_datastore_product(self):
        return self.env['of.datastore.supplier'].link_products(self._ids)

class ProductSupplierInfo(models.Model):
    _inherit = ['product.supplierinfo', 'of.datastore.centralized']









    def _read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lit les données des produits dans leur base fournisseur.
        @param ids: id modifié des produits, en valeur négative
        @param create_mode: En mode create on ne renvoie pas les champs non trouvés (remplis avec False ou [])
                            En mode create on remplit seller_ids
        """
        supplier_obj = self.env['of.datastore.supplier']
        res = []

        fields_to_read.pop('id', False) # Le champ id sera de toute façon ajouté, le laisser génèrera des erreurs

        # Produits par fournisseur
        datastore_supplierinfo_ids = {}
        for i in self._ids:
            supplier_id = -i / DATASTORE_IND
            datastore_supplierinfo_ids.setdefault(supplier_id, []).append((-i) % DATASTORE_IND)

        suppliers = supplier_obj.browse(datastore_supplierinfo_ids.keys())
        clients = suppliers.of_datastore_connect()
        try:
            # Champs a valeurs specifiques
            fields_defaults = {
                'name' : lambda:supplier.partner_id.id,
                'company_id': lambda: False,
                'product_id': False,
            }

            fields_defaults = {k:v for k, v in fields_defaults.iteritems() if k in fields_to_read}

            datastore_fields = [field for field in fields_to_read if field not in self._get_datastore_unused_fields() + fields_defaults.keys()]

            m2o_fields = [field for field in datastore_fields
                          if self._all_columns[field].column._type  == 'many2one'
                          and field != 'datastore_supplier_id']

            for supplier_id, supplierinfo_ids in datastore_supplierinfo_ids.iteritems():
                supplier = supplier_obj.browse(supplier_id)
                client = clients[supplier_id]
                ds_supplierinfo_obj = self.of_datastore_get_model(client, 'product.supplierinfo')

                if datastore_fields:
                    datastore_supplierinfo_data = self.of_datastore_read(ds_supplierinfo_obj, supplierinfo_ids, datastore_fields, '_classic_read')
                else:
                    # Si il n'y a plus aucun field, ds_supplierinfo_obj.read lirait TOUS les field disponibles, ce qui aurait l'effet inverse (et génèrerait des erreurs de droits)
                    datastore_supplierinfo_data = [{'id': supplierinfo_id} for supplierinfo_id in supplierinfo_ids]
                supplier_value = supplier_id * DATASTORE_IND

                if not create_mode:
                    # Les champs manquants dans la table du fournisseur ne sont pas renvoyés, sans générer d'erreur
                    # Il faut donc leur attribuer une valeur par défaut (False ou [] pour des One2many)
                    # Utilisation de _all_columns pour récupérer les colonnes de product_template également
                    datastore_defaults = {field: [] if self._all_columns[field].column._type in ('one2many', 'many2many') else False
                                          for field in fields_to_read if field not in datastore_supplierinfo_data[0]}

                # Traitement des données
                match_dicts = {}

                # Conversion des champs many2one
                for field in m2o_fields:
                    if field not in datastore_supplierinfo_data[0]:
                        continue
                    # Conversion du many2one pour la base courante
                    obj = self._all_columns[field].column._obj
                    res_ids = []
                    for vals in datastore_supplierinfo_data:
                        if vals[field]:
                            res_id = supplier.datastore_match(client, obj, vals[field][0], match_dicts, create=create_mode)
                            vals[field] = res_id
                            if res_id and res_id not in res_ids: res_ids.append(res_id)

                    if not create_mode:
                        # Conversion au format many2one (id, name)
                        obj_obj = self.env[obj].sudo()
                        res_names = {v[0]:v for v in obj_obj.name_get(res_ids)}
                        for vals in datastore_supplierinfo_data:
                            if vals[field]:
                                vals[field] = res_names[vals[field]]
                res += datastore_supplierinfo_data
        finally:
            supplier_obj.free_connection(clients)
        return res

# Création/édition d'objets incluant un article centralisé
class OfDatastoreProductReference(models.AbstractModel):
    _name = 'of.datastore.product.reference'

    @api.model
    def create(self, vals):
        # par défaut .get() retourne None si la clef n'existe pas, et None == -1
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).datastore_import()
        return super(OfDatastoreProductReference, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).datastore_import()
        return super(OfDatastoreProductReference, self).write(vals)

# class of_kit_relation(osv.osv):
#     _name = 'of.kit.relation'
#     _inherit = ['of.kit.relation', 'of.datastore.product.reference', 'of.datastore.centralized']
#     _description = "Gestion des kits"
# 
#     def _read_datastore(self, cr, uid, ids, fields_to_read, context=None):
#         u"""
#         Lit les donnees des kits dans leur base fournisseur.
#         @param ids: id modifié des produits, en valeur négative
#         """
#         supplier_obj = self.pool['of.datastore.supplier']
#         product_obj = self.pool['product.product']
#         res = []
# 
#         # Kits par fournisseur
#         datastore_kit_ids = {}
#         for i in ids:
#             supplier_id = -i / DATASTORE_IND
#             datastore_kit_ids.setdefault(supplier_id,[]).append((-i)%DATASTORE_IND)
# 
#         supplier_ids = datastore_kit_ids.keys()
# 
#         clients = supplier_obj.connect(cr, uid, supplier_ids, context=context)
#         try:
#             for supplier_id, kit_ids in datastore_kit_ids.iteritems():
#                 client = clients[supplier_id]
#                 ds_kit_obj = client.model('of.kit.relation')
#     
#                 # Donnees de la base fournisseur
#                 kits_data = ds_kit_obj.read(kit_ids, [])
#                 ds_product_ids = [kit['product_id'][0] for kit in kits_data]
#     
#                 # Detection des composants du kit deja importes
#                 product_ids = product_obj.search(cr, uid, [('datastore_supplier_id','=',supplier_id),('datastore_product_id','in',ds_product_ids)], context=context)
#                 products = product_obj.read(cr, uid, product_ids, ['datastore_product_id'], context=context)
#     
#                 product_match = {product['datastore_product_id']:product['id'] for product in products}
#                 product_names = dict(product_obj.name_get(cr, uid, product_ids, context=context))
#     
#                 # Affectation des ids des composants
#                 supplier_value = supplier_id * DATASTORE_IND
#                 for kit in kits_data:
#                     product_id,product_name = kit['product_id']
#                     if product_id in product_match:
#                         # Composant deja importe
#                         product_id = product_match[product_id]
#                         product_name = product_names[product_id]
#                     else:
#                         # Composant virtuel
#                         product_id = -(product_id + supplier_value)
#                     kit['product_id'] = (product_id,product_name)
#                     kit['id'] = -(kit['id'] + supplier_value)
#                 res += kits_data
#         finally:
#             supplier_obj.free_connection(clients)
#         return res

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'of.datastore.product.reference']

class SaleOrderLineComp(models.Model):
    _name = 'sale.order.line.comp'
    _inherit = ['sale.order.line.comp', 'of.datastore.product.reference']

class AccountInvoiceLine(models.Model):
    _name = 'account.invoice.line'
    _inherit = ['account.invoice.line', 'of.datastore.product.reference']

class AccountInvoiceLineComp(models.Model):
    _name = 'account.invoice.line.comp'
    _inherit = ['account.invoice.line.comp', 'of.datastore.product.reference']

class PurchaseOrderLine(models.Model):
    _name =  'purchase.order.line'
    _inherit = ['purchase.order.line', 'of.datastore.product.reference']

class StockInventoryLine(models.Model):
    _name = 'stock.inventory.line'
    _inherit = ['stock.inventory.line', 'of.datastore.product.reference']
