# -*- coding: utf-8 -*-
import copy

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.osv.expression import NEGATIVE_TERM_OPERATORS, TERM_OPERATORS_NEGATION, TRUE_LEAF, FALSE_LEAF

DATASTORE_IND = 100000000  # 100.000.000 ids devraient suffire pour les produits. Les chiffres suivants serviront pour le fournisseur

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
    _description = u"Connecteur au tarif centralisé"
    _rec_name = 'db_name'
    _order="db_name"

    brand_ids = fields.One2many('of.product.brand', 'datastore_supplier_id', string='Allowed brands')
    datastore_brand_ids = fields.One2many(
        'of.datastore.supplier.brand', compute='_compute_datastore_brand_ids', inverse=lambda *args:True,
        string='Supplier brands')
#     product_ids = fields.One2many(related='brand_ids.product_ids', string='Products')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u'Une connexion à cette base existe déjà')
    ]

    @api.depends()
    def _compute_datastore_brand_ids(self):
        supplier_brand_obj = self.env['of.datastore.supplier.brand']
        for supplier in self:
            datastore_brands = False
            client = self.of_datastore_connect()[self.id]
            if not isinstance(client, basestring):
                ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
                ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
                if ds_brand_ids:
                    id_add = DATASTORE_IND * supplier.id
                    ds_brand_ids = [brand_id + id_add for brand_id in ds_brand_ids]
                    datastore_brands = supplier_brand_obj.browse(ds_brand_ids)
            supplier.datastore_brand_ids = datastore_brands


#     @api.depends()
#     def _compute_datastore_brand_ids(self):
#         supplier_brand_obj = self.env['of.datastore.supplier.brand']
#         default_ds_brand_name = _('Error')
#         for supplier in self:
#             supplier_brand_data = {
#                 brand.datastore_brand_id: {
#                     'name': default_ds_brand_name,
#                     'datastore_brand_id': brand.datastore_brand_id,
#                     'brand_id': brand.id,
#                     'note_maj': '',
#                 } for brand in supplier.brand_ids
#             }
# 
#             client = self.of_datastore_connect()[self.id]
#             if not isinstance(client, basestring):
#                 ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
#                 ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
#                 ds_brand_data = self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['name', 'note_maj'])
#                 for data in ds_brand_data:
#                     if data['id'] in supplier_brand_data:
#                         supplier_brand_data[data['id']]['name'] = data['name']
#                         supplier_brand_data[data['id']]['note_maj'] = data['note_maj']
#                     else:
#                         supplier_brand_data[data['id']] = {
#                             'name': data['name'],
#                             'datastore_brand_id': data['id'],
#                             'brand_id': False,
#                             'note_maj': data['note_maj'],
#                         }
# 
# 
# 
#             supplier_brands = [(0, 0, data) for data in supplier_brand_data.itervalues()]
# #             supplier_brands = supplier_brand_obj.browse()
# #             for data in supplier_brand_data.itervalues():
# #                 supplier_brands |= supplier_brand_obj.new(data)
# #             supplier_brands = supplier_brands.sorted(key=lambda d: (d.name, d.brand_id and d.brand_id.name))
#             supplier.datastore_brand_ids = supplier_brands

#     def _inverse_datastore_brand_ids(self):
#         for supplier in self:
#             brand_match = {r.brand_id: r.datastore_brand_id for r in supplier.datastore_brand_ids if r.brand_id}
#             for brand in supplier.brand_ids:
#                 ds_brand_id = brand_match.pop(brand, False)
#                 if ds_brand_id:
#                     if ds_brand_id != brand.datastore_brand_id:
#                         brand.datastore_brand_id = ds_brand_id
#                 else:
#                     brand.datastore_supplier_id = False
#                     brand.datastore_brand_id = False
#             for brand, ds_brand_id in brand_match.iteritems():
#                 brand.datastore_supplier_id = supplier.id
#                 brand.datastore_brand_id = ds_brand_id

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
    def button_dummy(self):
        return True


    @api.multi
    def button_import_brands(self):
        self.ensure_one()
        wizard_obj = self.env['of.datastore.import.brand']
        client = self.of_datastore_connect()[self.id]
        if isinstance(client, basestring):
            raise UserError(u'Échec de la connexion à la base centrale')
        ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
        ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
        ds_brand_data = self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['name', 'code', 'logo', 'note_maj'])
        brand_names = self.env['of.product.brand'].search([]).mapped('name')

        wizard = wizard_obj.create({
            'datastore_supplier_id': self.id,
            'line_ids': [(0, 0, {
                'datastore_brand_id': ds_brand['id'],
                'name': ds_brand['name'],
                'code': ds_brand['code'],
                'logo': ds_brand['logo'],
                'note_maj': ds_brand['note_maj'],
                'state': 'done' if ds_brand['name'] in brand_names else 'do',
                }) for ds_brand in ds_brand_data]
            })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': wizard._name,
            'res_id': wizard.id,
            'target': 'new',
        }
#     @api.multi
#     def action_import_brands(self):
#         self.ensure_one()
#         brand_obj = self.env['of.product.brand']
#         client = self.of_datastore_connect()[self.id]
#         if isinstance(client, basestring):
#             raise UserError(u'Échec de la connexion à la base centrale')
#         ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
#         ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
#         ds_brand_data = self.of_datastore_read(ds_brand_obj, ds_brand_ids)
#         # Filtre des marques déjà existantes
#         ds_brand_data = {
#             key: val
#             for key, val in ds_brand_data.iteritems()
#             if val['prefix'] not in brand_obj.search([]).mapped('prefix')
#         }
#         for vals in ds_brand_data:
#             vals['datastore_supplier_id'] = vals.pop('id')
#             brand_obj.create(vals)

class OfDatastoreSupplierBrand(models.AbstractModel):
    _name = 'of.datastore.supplier.brand'

    name = fields.Char(string="Marque fournisseur", required=True, readonly=True)
    datastore_brand_id = fields.Integer(string="Identifiant marque fournisseur", required=True, readonly=True)
    brand_id = fields.Many2one('of.product.brand', String="Correspondance")
    product_count = fields.Integer(string='# products', readonly=True)
    note_maj = fields.Text(string='Notes MAJ', readonly=True)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        brand_obj = self.env['of.product.brand']
        ds_supplier_obj = self.env['of.datastore.supplier']
        default_ds_brand_name = _('Error')
        result = []
        for ds_brand_full_id in self.ids:
            ds_supplier_id = ds_brand_full_id / DATASTORE_IND
            ds_brand_id = ds_brand_full_id % DATASTORE_IND

            brand = brand_obj.search([('datastore_supplier_id', '=', ds_supplier_id), ('datastore_brand_id', '=', ds_brand_id)])

            vals = {
                'id': ds_brand_full_id,
                'brand_id': brand and brand.id or False,
                'name': default_ds_brand_name,
                'datastore_brand_id': False,
                'note_maj': '',
                'product_count': False,
            }

            ds_supplier = ds_supplier_obj.browse(ds_supplier_id)
            client = ds_supplier.of_datastore_connect()[ds_supplier_id]
            if not isinstance(client, basestring):
                ds_brand_obj = ds_supplier.of_datastore_get_model(client, 'of.product.brand')
                ds_brand_data = ds_supplier.of_datastore_read(ds_brand_obj, [ds_brand_id], ['name', 'note_maj', 'product_count'])[0]
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
            old_brand = brand_obj.search([('datastore_supplier_id', '=', ds_supplier_id), ('datastore_brand_id', '=', ds_brand_id)])
            if old_brand:
                if new_brand_id != old_brand.id:
                    old_brand.write({'datastore_supplier_id': False, 'datastore_brand_id': False})
                    old_brand = False
            if new_brand_id and not old_brand:
                new_brand = brand_obj.browse(new_brand_id)
                new_brand.write({'datastore_supplier_id': ds_supplier_id, 'datastore_brand_id': ds_brand_id})
        return True


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    datastore_supplier_id = fields.Many2one('of.datastore.supplier', string=u"Connecteur tarif centralisé")
    datastore_brand_id = fields.Integer(string=u"Identifiant tarif centralisé")

    all_categ_ids = fields.One2many(
        'of.import.product.categ.config', compute="_compute_all_categ_ids", inverse="_inverse_all_categ_ids", string="Catégories")
#     error_msg = fields.Char(string='Connection message', compute='_compute_all_categ_ids')
    datastore_note_maj = fields.Text(string='Notes MAJ', compute='_compute_datastore_note_maj')
    datastore_product_count = fields.Integer(
        '# Products', compute='_compute_datastore_note_maj',
        help="The number of products of this brand")

    @api.depends('datastore_supplier_id')
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
#                 brand.error_msg = client
#                 brand.note_maj = ''
                brand.datastore_note_maj = 'Error\n' + client
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
            ds_brand_ids = self.of_datastore_search(ds_brand_obj, [('code', 'in', supplier.brand_ids.mapped('code'))])
            brand_notes = {brand['code']: brand['note']
                           for brand in self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['code', 'note'])}

            brand_notes = []
            for brand in supplier.brand_ids:
                brand_note = brand_notes.get(brand.code, '').strip()
                if brand_note:
                    brand_notes.append("%s\n%s" % (brand.name, brand_note))

            supplier.categ_ids = [data[i] for i in ds_categ_ids]  # Mise des catégories dans l'ordre défini par ds_categ_ids
#             brand.datastore_note_maj = 
#             brand.error_msg = u"Connexion réussie"
#             brand.note_maj = "\n\n".join("notes")

    def _inverse_categ_ids(self):
        for supplier in self:
            supplier.stored_categs = supplier.categ_ids

    @api.depends('datastore_supplier_id')
    def _compute_datastore_note_maj(self):
        """
        @todo: Le matching de la marque devrait se faire sur le nom ou un id plutôt que sur le préfixe.
               En effet, le distributeur peut vouloir un préfixe différent.
        """
        suppliers_brands = {}

        # Regroupement des marques par base centrale
        for brand in self:
            if brand.datastore_supplier_id:
                suppliers_brands.setdefault(brand.datastore_supplier_id, []).append(brand.name)

        clients = self.mapped('datastore_supplier_id').of_datastore_connect()
        suppliers_data = {}
        for supplier, brand_names in suppliers_brands.iteritems():
            client = clients[supplier.id]
            if isinstance(client, basestring):
                suppliers_data[supplier] = u"Échec de la connexion à la base centrale\n\n" + client
                continue
            ds_brand_obj = supplier.of_datastore_get_model(client, 'of.product.brand')
            ds_brand_ids = supplier.of_datastore_search(ds_brand_obj, [('name', 'in', brand_names)])
            suppliers_data[supplier] = {
                data['name']: (data['note_maj'], data['product_count']) 
                for data in supplier.of_datastore_read(ds_brand_obj, ds_brand_ids, ['name', 'note_maj', 'product_count'])
            }

        for brand in self:
            product_count = 0
            if not brand.datastore_supplier_id:
                note = u"Marque non associée à une base centrale"
            elif isinstance(suppliers_data[brand.datastore_supplier_id], basestring):
                note = suppliers_data[brand.datastore_supplier_id]
            elif brand.name not in suppliers_data[brand.datastore_supplier_id]:
                note = u"Marque non présente sur la base centrale"
            else:
                note, product_count = suppliers_data[brand.datastore_supplier_id][brand.name]
            brand.datastore_note_maj = note
            brand.datastore_product_count = product_count

    @api.multi
    def datastore_match(self, client, obj, res_id, res_name, product, match_dicts, create=True):
        """ Tente d'associer un objet de la base centrale à un id de la base de l'utilisateur
        @param client: client erppeek connecté à la base du fournisseur
        @param obj: nom de l'objet à faire correspondre
        @param res_id: id de l'instance de l'objet à faire correspondre
        @param match_dicts: dictionnaire des correspondances par objet
        @return: Entier correspondant a l'id de l'object correspondant dans la base courante, ou False
        """
        def datastore_matching_model(obj_name, obj_id):
            """ Teste si une correspondance existe dans la table ir_model_data
            @warning: Cette façon de faire est dangereuse car les éléments ont pu être modifiés à la main, ne l'utiliser que pour de rares modèles.
            """
            model_ids = ds_supplier_obj.of_datastore_search(ds_model_obj, [('model', '=', obj_name), ('res_id', '=', obj_id)])
            if not model_ids:
                return False
            model = ds_supplier_obj.of_datastore_read(ds_model_obj, model_ids, ['module','name'])[0]
            res_id = model_obj.search([('module', '=', model['module']), ('name', '=', model['name'])]).id
            # Dans certains cas, un objet a pu être supprimé en DB mais pas sa référence dans ir_model_data
            res_id = res_id and self.env[obj_name].search([('id', '=', res_id)]).id
            return res_id
        # --- Gestion des cas particuliers ---
        if obj == self._name:
            return self
        if obj == 'product.category':
            return self.compute_product_categ(res_name, product)

        match_dict = match_dicts.setdefault(obj,{})

        # Recherche de correspondance dans les valeurs précalculées
        if res_id in match_dict:
            return match_dict[res_id]

        # Recherche de correspondance dans les identifiants externes (ir_model_data)
        model_obj = self.env['ir.model.data']
        ds_supplier_obj = self.env['of.datastore.supplier']
        ds_model_obj = client.get_model('ir.model.data')
        ds_obj_obj = client.get_model(obj)
        result = False

        # Calcul de correspondance en fonction de l'objet
        obj_obj = self.env[obj]
        if obj == 'product.uom.categ':
            result = datastore_matching_model(obj, res_id)
            if not result:
                result = obj_obj.search([('name', '=', res_name)], limit=1)
                if not result:
                    raise ValidationError(u"Catégorie d'UDM inexistante : " + res_name)
        elif obj == 'product.uom':
            # Etape 1 : Déterminer la catégorie d'udm
            ds_obj = ds_supplier_obj.of_datastore_read(ds_obj_obj, [res_id], ['category_id', 'factor', 'uom_type', 'rounding'])[0]

            categ = self.datastore_match(client, 'product.uom.categ', ds_obj['category_id'][0], ds_obj['category_id'][1],
                                         product, match_dicts)

            # Etape 2 : Vérifier si l'unité de mesure existe
            uoms = obj_obj.search([('factor', '=', ds_obj['factor']),
                                   ('uom_type', '=', ds_obj['uom_type']),
                                   ('category_id', '=', categ.id)])

            if uoms:
                if len(uoms) > 1:
                    # Ajout d'un filtre sur le nom pour préciser la recherche
                    uoms = obj_obj.search([('id', 'in', uoms.ids), ('name', '=ilike', res_name)]) or uoms
                if len(uoms) > 1:
                    # Ajout d'un filtre sur la précision de l'arrondi pour préciser la recherche
                    uoms = obj_obj.search([('id', 'in', uoms.ids),('rounding', '=', ds_obj['rounding'])]) or uoms
                result = uoms[0]
            elif create:
                # Etape 3 : Créer l'unité de mesure
                uom_data = {
                    'name'       : res_name,
                    'uom_type'   : ds_obj['uom_type'],
                    'factor'     : ds_obj['factor'],
                    'category_id': categ.id,
                    'rounding'   : ds_obj['rounding'],
                }
                result = obj_obj.create(uom_data)
        match_dict[res_id] = result
        return result


class OfDatastoreCentralized(models.AbstractModel):
    _name = 'of.datastore.centralized'

    of_datastore_res_id = fields.Integer(string="Identifiant base fournisseur")

    @api.model
    def _get_datastore_unused_fields(self):
        # Champs qu'on ne veut pas récupérer chez le fournisseur (quantités en stock)
        cr = self._cr

        # On ne veut aucun des champs ajoutes par les modules stock, mrp, purchase
#         cr.execute("SELECT DISTINCT f.name "
#                    "FROM ir_model_data AS d "
#                    "INNER JOIN ir_model_fields AS f "
#                    "  ON d.res_id=f.id "
#                    "WHERE d.model = 'ir.model.fields' "
#                    "  AND f.model IN ('product.product','product.template') "
#                    "  AND d.module IN ('mrp','procurement','stock')")
        cr.execute("SELECT f.name "
                   "FROM ir_model_data AS d "
                   "INNER JOIN ir_model_fields AS f "
                   "  ON d.res_id=f.id "
                   "WHERE d.model = 'ir.model.fields' "
                   "  AND f.model = %s "
                   "  AND d.module IN ('mrp','procurement','stock')", self._name)
        res = [row[0] for row in cr.fetchall()]

        # Ajout de certains champs du module product
        res += [
        ]

        # On ne veut pas non-plus les champs one2many ou many2many (seller_ids, packagind_ids, champs liés aux variantes....)
        # On conserve les lignes de kits
        for field_name, field in self._fields.iteritems():
            if field.type in ('one2many','many2many'):
                if field_name != 'kit_line_ids' and field_name not in res:
                    res.append(field_name)
        return res

#     @api.model
#     def _get_datastore_fields(self):
#         return (
#             'brand_id',
#             'price',
#             'list_price',
#             'cost',
#             'code', # A vérifier : champ calculé
#             'default_code',
#             'categ_id',
#             'lst_price',
#             'standard_price',
#             'uom_id',
#             'uom_po_id',
#             'seller_ids', # A compléter : champs relationnels ajoutés dans of_product
#             """
#             ... en gros tous les champs sont à lire ><
#             """,
#         )

    @api.multi
    def _read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lit les donnees des produits dans leur base fournisseur.
        @param ids: id modifié des produits, en valeur négative
        @param create_mode: En mode create on ne renvoie pas les champs non trouvés (remplis avec False ou [])
                            En mode create on remplit seller_ids
        """
        supplier_obj = self.env['of.datastore.supplier']
        result = []

        if 'id' in fields_to_read: # Le champ id sera de toute façon ajouté, le laisser génèrera des erreurs
            fields_to_read.remove('id')

        # Articles par fournisseur
        datastore_product_ids = {}

        # Produits par fournisseur
        for full_id in self._ids:
#            brand_id = -full_id / DATASTORE_IND
#            brand_product_ids.setdefault(brand_id, []).append((-full_id) % DATASTORE_IND)

            supplier_id = -full_id / DATASTORE_IND
            datastore_product_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        suppliers = supplier_obj.browse(datastore_product_ids.keys())
        clients = suppliers.of_datastore_connect()

#        suppliers = {supplier.id: supplier for supplier in suppliers}

        # Champs a valeurs spécifiques
        fields_defaults = {
            'of_datastore_supplier_id': lambda: supplier_m2o_id,
            'of_datastore_res_id'     : lambda: vals['id'],
        }

        fields_defaults = {k:v for k,v in fields_defaults.iteritems() if k in fields_to_read}
        if create_mode:
            # Ajout des champs nécessaires à la creation du product_supplierinfo
            for field in ('sale_delay',):
                if field not in fields_to_read:
                    fields_to_read.append(field)

            # Creation de la relation fournisseur
            fields_defaults['seller_ids'] = lambda: [(0, 0, {
                    'name'   : supplier.partner_id.id,
                    'min_qty': 1,
                    'delay'  : vals['sale_delay'],
                })]

        datastore_fields = [field for field in fields_to_read if field not in self._get_datastore_unused_fields()]

        # Ajout de champs nécessaires aux calculs
        added_fields = [field for field in ('brand_id', 'categ_id', 'uom_id', 'uom_po_id', 'list_price')
                        if field not in datastore_fields]
        datastore_fields += added_fields

        m2o_fields = [field for field in datastore_fields
                      if self._fields[field].type  == 'many2one'
                      and field != 'of_datastore_supplier_id']

        o2m_fields = ['kit_line_ids'] # :-)

        for supplier_id, product_ids in datastore_product_ids.iteritems():
            supplier_value = supplier_id * DATASTORE_IND
            client = clients[supplier_id]
            supplier = supplier_obj.browse(supplier_id)
            ds_product_obj = client.get_model(self._name)

            if datastore_fields:
                datastore_product_data = supplier_obj.of_datastore_read(ds_product_obj, product_ids, datastore_fields, '_classic_read')
            else:
                # Si il n'y a plus aucun field, ds_product_obj.read lirait TOUS les field disponibles, ce qui aurait l'effet inverse (et genererait des erreurs de droits)
                datastore_product_data = [{'id':product_id} for product_id in product_ids]

            if not create_mode:
                # Les champs manquants dans la table du fournisseur ne sont pas renvoyes, sans generer d'erreur
                # Il faut donc leur attribuer une valeur par defaut (False ou [] pour des one2many)
                datastore_defaults = {field: [] if self._fields[field].type in ('one2many','many2many') else False
                                      for field in fields_to_read if field not in datastore_product_data[0]}

            # Traitement des donnees
            match_dicts = {}
            match_dicts['brand_id'] = {brand.datastore_brand_id: brand for brand in supplier.brand_ids}

            datastore_read_m2o_fields = [field for field in m2o_fields if field in datastore_product_data[0]]
            field_res_ids = {field: set() for field in datastore_read_m2o_fields}
            for vals in datastore_product_data:
                # --- Calculs préalables ---
                brand = match_dicts['brand_id'][vals['brand_id'][0]]
                product = self.search([('of_datastore_res_id', '=', vals['id'])])
                if self._name == 'product.product':
                    product = product.product_tmpl_id
                categ_name = vals['categ_id'][1]
                obj_dict = {}

                # ---- Champs many2one ---
                for field in datastore_read_m2o_fields:
                    if field == 'product_tmpl_id':
                        # product_tmpl_id ne doit pas etre False, notamment a cause de la fonction pricelist.price_get_multi qui genererait une erreur
                        # Pour eviter des effets de bord, on met une valeur negative
                        if create_mode:
                            vals[field] = -(vals[field][0] + supplier_value)
                        else:
                            vals[field] = (-(vals[field][0] + supplier_value), vals[field][1])
                        continue

                    # Conversion du many2one pour la base courante
                    if vals[field]:
                        obj = self._fields[field].comodel_name
                        res = brand.datastore_match(client, obj, vals[field][0], vals[field][1], product, match_dicts, create=create_mode)
                        if field in ('categ_id', 'uom_id', 'uom_po_id'):
                            obj_dict[field] = res
                        res_id = res and res.id
                        vals[field] = res_id
                        if res_id:
                            field_res_ids[field].add(res_id)

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
                        vals[field] = [(0, 0, obj_obj.copy_data(line_id)) for line_id in line_ids]
                    else:
                        # Conversion en id datastore
                        # Parcours avec indice pour ne pas recreer la liste
                        vals[field] = line_ids

                # --- Champs spéciaux ---
                
                supplier_m2o_id = create_mode and supplier_id or supplier.name_get()[0]
                # Preparation des variables
                list_price = vals['list_price']
                vals.update(brand.compute_product_price(list_price, categ_name, obj_dict['uom_id'], obj_dict['uom_po_id'],
                                                        product=product, price=None, remise=None))

                # Calcul des valeurs specifiques
                for field,val in fields_defaults.iteritems():
                    vals[field] = val()
                if create_mode:
                    del vals['id']
                else:
                    vals['id'] = -(vals['id'] + supplier_value)
                    vals.update(datastore_defaults)

            if not create_mode:
                # Conversion au format many2one (id,name)
                for field, res_ids in field_res_ids.iteritems():
                    if not res_ids:
                        continue

                    obj = self._fields[field].comodel_name
                    res_obj = self.env[obj].browse(res_ids)
                    res_names = {v[0]:v for v in res_obj.sudo().name_get()}
                    for vals in datastore_product_data:
                        if vals[field]:
                            vals[field] = res_names[vals[field]]

#             for field in m2o_fields:
#                 if field not in datastore_product_data[0]:
#                     continue
#                 if field == 'product_tmpl_id':
#                     # product_tmpl_id ne doit pas etre False, notamment a cause de la fonction pricelist.price_get_multi qui genererait une erreur
#                     # Pour eviter des effets de bord, on met une valeur negative
#                     for vals in datastore_product_data:
#                         if vals[field]:
#                             if create_mode:
#                                 vals[field] = -vals[field][0]
#                             else:
#                                 vals[field][0] *= -1
#                     continue
# 
#                 # Conversion du many2one pour la base courante
#                 obj = self._fields[field].comodel_name
#                 res_ids = []
#                 for vals in datastore_product_data:
#                     if vals[field]:
#                         res_id = brand.datastore_match(client, obj, vals[field][0], match_dicts, create=create_mode)
#                         vals[field] = res_id
#                         if res_id and res_id not in res_ids: res_ids.append(res_id)
# 
#                 if not create_mode:
#                     # Conversion au format many2one (id,name)
#                     obj_obj = self.pool[obj]
#                     res_names = {v[0]:v for v in obj_obj.name_get(1, res_ids)}
#                     for vals in datastore_product_data:
#                         if vals[field]:
#                             vals[field] = res_names[vals[field]]

#             # Conversion des champs one2many/many2many
#             for field in o2m_fields:
#                 if field not in datastore_fields:
#                     continue
#                 for vals in datastore_product_data:
#                     if not vals[field]:
#                         continue
#                     line_ids = [-(line_id + supplier_value) for line_id in vals[field]]
#                     if create_mode:
#                         # Preparation des lignes
#                         obj = self._fields[field].comodel_name
#                         obj_obj = self.pool[obj]
#                         vals[field] = [(0, 0, obj_obj.copy_data(line_id)) for line_id in line_ids]
#                     else:
#                         # Conversion en id datastore
#                         # Parcours avec indice pour ne pas recreer la liste
#                         vals[field] = line_ids

#             # Champs particuliers
#             supplier_m2o_id = create_mode and supplier_id or supplier_obj.name_get([supplier_id])[0]
#             for vals in datastore_product_data:
#                 # Preparation des variables
#                 price_remise   = vals['price_remise']
#                 standard_price = vals['standard_price']
#                 price_extra    = vals['price_extra']
#                 list_pvht      = vals['list_pvht']
#                 for field in added_fields:
#                     del vals[field]
# 
#                 eval_dict = {
#                     'rc'   : price_remise,
#                     'ra'   : price_remise,
#                     'cumul': supplier_obj.compute_remise,
#                 }
# 
#                 # Calcul de la remise sur prix d'achat
#                 remise_eval = vals.pop('remise_eval')
#                 remise = safe_eval(remise_eval, eval_dict)
#                 if remise != price_remise:
#                     if remise >= 100:
#                         standard_price = 0.0
#                     else:
#                         standard_price *= (100-remise)/(100.0-price_remise)
# 
#                 # Calcul prix de vente modifies
#                 eval_dict.update({
#                     'r'  : remise,
#                     'pv' : price_extra + standard_price * 100 / (100.0 - remise) if remise<100 else list_pvht,
#                     'tf' : price_extra,
#                 })
#                 price_eval = vals.pop('price_ttc_eval')
#                 list_pvht = safe_eval(price_eval, eval_dict)
#                 price_margin = standard_price and round((list_pvht - price_extra) / standard_price, margin_prec) or 1
#                 remise = 100 - 100.0 / price_margin
# 
#                 # Calcul des valeurs specifiques
#                 for field,val in fields_defaults.iteritems():
#                     vals[field] = val()
#                 if create_mode:
#                     del vals['id']
#                 else:
#                     vals['id'] = -(vals['id'] + supplier_value)
#                     vals.update(datastore_defaults)
            result += datastore_product_data

        return result

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        new_ids = [i for i in self._ids if i>0]
        datastore_ids = [i for i in self._ids if i<0]
#         if self._context.get('of_datastore_product_search'):
#             self = self.with_context(of_datastore_product_search=False)

        # Produits sur la base courante
        res = super(OfDatastoreCentralized, self.browse(new_ids)).read(fields, load=load)
        
        if datastore_ids:
            # Si fields est vide, on récupère tous les champs accessibles pour l'objet (copié depuis BaseModel.read())
            self.check_access_rights('read')
            fields = self.check_field_access_rights('read', fields)
            res += self.browse(datastore_ids)._read_datastore(fields, create_mode=False)
        return res

    @api.model
    def of_datastore_update_domain(self, domain):
        """
        Vérifie si le domaine indique une recherche sur une base de données fournisseur.
        Si oui, retourne le domaine de recherche adapté pour la base de données fournisseur.
        @requires: Si args contient un tuple dont le premier argument est 'ds_supplier_search_id', le second argument doit être '='
        @return: Id du fournisseur (of.datastore.supplier) ou False sinon, suivi du nouveau domaine de recherche
        """
#         if not self._context.get('of_datastore_product_search'):
#             return False, domain
        if 'of_datastore_product_search' not in domain:
            return False, domain

        domain = [arg for arg in domain if arg != 'of_datastore_product_search']

        # Recherche des marques
        brand_domain = []
        for arg in domain:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0] == 'brand_id':
                _, operator, right = arg
                # resolve string-based m2o criterion into IDs
                if isinstance(right, basestring) or \
                        right and isinstance(right, (tuple, list)) and all(isinstance(item, basestring) for item in right):
                    brand_domain.append(('name', operator, right))
                else:
                    brand_domain.append(('id', operator, right))
        brands = self.env['of.product.brand'].search(brand_domain)
        ds_supplier = brands.mapped('datastore_supplier_id')

        if not ds_supplier:
            if brands:
                raise UserError(_('Selected brands are not centralized : %s') % ", ".join(brands.mapped('name')))
            return False, FALSE_LEAF

        if len(ds_supplier) > 1:
            raise UserError(_('You must select one or several brands using the same centralized database (provided by the same supplier).'))
        brands = brands.filtered('datastore_supplier_id')

        # Recherche des produits non déjà enregistrés
        if not self._context.get('datastore_stored'):
            self._cr.execute(
                'SELECT of_datastore_res_id '
                'FROM product_product '
                'WHERE brand_id in %s AND of_datastore_res_id IS NOT NULL',
                (tuple(brands.ids), ))
            orig_ids = [row[0] for row in self._cr.fetchall()]
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
        """ Convertit un élément du domaine pour utilisation sur la base centrale
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
        if not obj:
            result = (left, new_operator, [])
        # Conversion des ids courants en ids de la base centralisée
        elif obj._name == 'of.product.brand':
            # La correspondance des marques se fait sur le nom
            result = (left, operator, obj.mapped('name'))

        return result


#         # Duplication du domaine
#         domain = copy.deepcopy(domain)
# 
#         # Conversion des catégories de produits
#         for arg in domain:
#             if not isinstance(arg, (list, tuple)):
#                 continue
#             if arg[0].startswith('ds_'):
#                 arg[0] = arg[0][3:]
#             elif arg[0] == 'brand_id':
#                 
#                 pass
#                 
#                 
#                 
#             elif arg[0] == 'categ_id':
#                 if arg[1] == 'child_of':
#                     pass # @todo: Voir comment integrer ça joliment
#                 else:
#                     categ_ids = arg[2]
#                     if arg[1] == '=':
#                         arg[1] = 'in'
#                         categ_ids = [categ_ids]
#                     elif arg[1] in ('!=','<>'):
#                         arg[1] = 'not in'
#                         categ_ids = [categ_ids]
#                     self._cr.execute('SELECT DISTINCT orig_id '
#                                      'FROM of_datastore_product_category '
#                                      'WHERE supplier_id=%s AND categ_id IN %s', (supplier_id, tuple(categ_ids)))
#                     arg[2] = [row[0] for row in self._cr.fetchall()]
# 
# 
# 
# 
#         supplier_id = False
# 
#         # Duplication du domaine
#         domain = copy.deepcopy(domain)
#         # Détection de l'utilisation d'une base de fournisseur
#         for arg in domain:
#             if isinstance(arg, (list, tuple)) and arg[0] == 'ds_supplier_search_id':
#                 supplier_id = arg[2]
#                 # Le distributeur ne peut voir que les articles de la marque configurée pour ce fournisseur
#                 arg[0] = 1
#                 arg[1] = '='
#                 arg[2] = 1
#                 break
#         if not supplier_id:
#             # Pas de base fournisseur specifiée, recherche sur la base actuelle
#             return False, domain
# 
#         # Recherche des produits non deja enregistres
#         if not self._context.get('datastore_stored'):
#             self._cr.execute('SELECT datastore_product_id '
#                              'FROM product_product '
#                              'WHERE datastore_supplier_id=%s AND datastore_product_id IS NOT NULL',
#                              (supplier_id, ))
#             orig_ids = [row[0] for row in self._cr.fetchall()]
#             domain.append(('id', 'not in', orig_ids))
# 
#         # Conversion des catégories de produits
#         for arg in domain:
#             if not isinstance(arg, (list, tuple)):
#                 continue
#             if arg[0].startswith('ds_'):
#                 arg[0] = arg[0][3:]
#             elif arg[0] == 'categ_id':
#                 if arg[1] == 'child_of':
#                     pass # @todo: Voir comment integrer ça joliment
#                 else:
#                     categ_ids = arg[2]
#                     if arg[1] == '=':
#                         arg[1] = 'in'
#                         categ_ids = [categ_ids]
#                     elif arg[1] in ('!=','<>'):
#                         arg[1] = 'not in'
#                         categ_ids = [categ_ids]
#                     self._cr.execute('SELECT DISTINCT orig_id '
#                                      'FROM of_datastore_product_category '
#                                      'WHERE supplier_id=%s AND categ_id IN %s', (supplier_id, tuple(categ_ids)))
#                     arg[2] = [row[0] for row in self._cr.fetchall()]
#         return supplier_id, domain

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        brands, args = self.of_datastore_update_domain(args)

        # Recherche sur la base du fournisseur
        if brands:
            supplier = brands[0].datastore_supplier_id
#            brands = supplier.brand_ids
            # Ex: si la base n'a qu'une base centralisée, elle peut appeler les articles de la base distante sans autre filtre de recherche.
            # Dans ce cas, on ne veut pas les autres marques du fournisseur
            args = ['&', ('brand_id', 'in', brands.mapped('datastore_brand_id'))] + args

#            supplier = brands[0].datastore_supplier_id
            supplier_obj = self.env['of.datastore.supplier']

            # Exécution de la requête sur la base du fournisseur
            client = supplier.of_datastore_connect()[supplier.id]
            if isinstance(client, basestring):
                # Échec de la connexion à la base fournisseur
                raise UserError(u'Erreur accès '+supplier.name, client)

            ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)
            res = supplier_obj.of_datastore_search(ds_product_obj, args, offset, limit, order, count)

            if not count:
                supplier_value = supplier.id * DATASTORE_IND
                res = [-(product_id + supplier_value) for product_id in res]
#                 if len(brands) == 1:
#                     brand_value = brands.id * DATASTORE_IND
#                     res = [-(product_id + brand_value) for product_id in res]
#                 else:
#                     brand_ids = {brand.datastore_brand_id: brand.id * DATASTORE_IND for brand in brands}
#                     products = supplier_obj.of_datastore_read(ds_product_obj, res, ['brand_id'])
#                     res = [-(product['id'] + brand_ids[product['brand_id'][0]]) for product in products]
        else:
            # Éxecution de la requête sur la base courante
            res = super(OfDatastoreCentralized, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        return res

    def _of_datastore_name_search(self, res, brands, name, args, operator, limit):
        supplier = brands.mapped('datastore_supplier_id')
        if len(supplier._ids) != 1:
            # Les marques doivent être centralisées, une seule base centrale à la fois
            return res

        if limit != 8 or len(res) == limit:
            # La recherche sur une base fournisseur ne se fait en automatique que pour les recherches
            #   dynamiques des champs many2one (limit=8)
            return res
        if len(res) == 7:
            # Le 8e produit ne sert qu'a savoir si on affiche "Plus de resultats"
            return res + [False]

        # Recherche des produits dans la base centrale
        client = supplier.of_datastore_connect()[supplier.id]
        if isinstance(client, basestring):
            #Echec de la connexion a la base fournisseur
            return res

        brands = brands.filtered('datastore_supplier_id')

        # Recherche des produits non déjà enregistrés
        orig_ids = self.search([('brand_id', 'in', brands._ids), ('of_datastore_res_id', '!=', False)]).mapped('of_datastore_res_id')

        # Mise a jour des paramètres de recherche
        new_args = [('brand_id', 'in', brands.mapped('datastore_brand_id')), ('id', 'not in', orig_ids)] + args

        ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
        res2 = supplier.of_datastore_name_search(ds_product_obj, name, new_args, operator, limit-len(res))
        supplier_ind = DATASTORE_IND * supplier['id']
        res += [[-(pid + supplier_ind), pname] for pid, pname in res2]
        return res


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['product.template', 'of.datastore.centralized']

    # ce champ va permettre de faire une recherche sur le tarif centralisé
    of_datastore_supplier_id = fields.Many2one('of.datastore.supplier', related='brand_id.datastore_supplier_id')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, brands = self.of_name_search_extract_brands(name)
        new_args = args
        if brands:
            new_args = [('brand_id', 'in', brands._ids)] + args
        res = super(ProductTemplate, self).name_search(name, new_args, operator, limit)
        return self._of_datastore_name_search(res, brands, name, args, operator, limit)

    @api.multi
    def of_datastore_import(self):
        supplier_obj = self.env['of.datastore.supplier']
        supplier = supplier_obj.browse(-self.id / DATASTORE_IND)
        client = supplier.of_datastore_connect()[supplier.id]
        if isinstance(client, basestring):
            raise ValidationError(u"Erreur de connexion à la base centrale")

A continuer


        ds_product_obj = supplier_obj.of_datastore_get_model(client, 'of.product.product')
        ds_product_ids = supplier_obj.of_datastore_search(ds_brand_obj, [])
        if ds_brand_ids:
            id_add = DATASTORE_IND * supplier.id
            ds_brand_ids = [brand_id + id_add for brand_id in ds_brand_ids]
            datastore_brands = supplier_brand_obj.browse(ds_brand_ids)
        supplier.datastore_brand_ids = datastore_brands

        result = self.search([('brand_id', 'in', supplier.brand_ids._ids),
                              ('of_datastore_res_id', '=', (-self.id) % DATASTORE_IND)])
        
        if len(self._ids) == 1:
            # Detection de l'existance du produit
            # Ce cas peut se produire dans un object de type commance, si plusieurs lignes ont la meme reference
            supplier = self.env['of.datastore.supplier'].browse(-self.id / DATASTORE_IND)
            
            result = self.search([('brand_id', 'in', supplier.brand_ids._ids),
                                  ('of_datastore_res_id', '=', (-self.id) % DATASTORE_IND)])
            if result:
                return result[0]

        fields_to_read = [f for f,c in self._fields.iteritems()
                          if not c.compute
                          and f != 'product_tmpl_id']

        fields_to_read.append('kit_lines')

        result = []
        for product_data in self._read_datastore(cr, uid, product_ids, fields_to_read, create_mode=True, context=context):
            result.append(self.create(cr, uid, product_data, context=context))
        if single_id:
            result = result[0]
        return result


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ['product.product', 'of.datastore.centralized']

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, brands = self.env['product.template'].of_name_search_extract_brands(name)
        new_args = args
        if brands:
            new_args = [('brand_id', 'in', brands._ids)] + args
        res = super(ProductProduct, self).name_search(name, new_args, operator, limit)
        return self._of_datastore_name_search(res, brands, name, args, operator, limit)

    @api.multi
    def of_datastore_import(self):
        if len(self._ids) == 1:
            # Detection de l'existance du produit
            # Ce cas peut se produire dans un object de type commance, si plusieurs lignes ont la meme reference
            supplier = self.env['of.datastore.supplier'].browse(-self.id / DATASTORE_IND)
            
            result = self.search([('brand_id', 'in', supplier.brand_ids._ids),
                                  ('of_datastore_res_id', '=', (-self.id) % DATASTORE_IND)])
            if result:
                return result[0]

        fields_to_read = [f for f,c in self._fields.iteritems()
                          if not c.compute
                          and f != 'product_tmpl_id']

        fields_to_read.append('kit_lines')

        result = []
        for product_data in self._read_datastore(cr, uid, product_ids, fields_to_read, create_mode=True, context=context):
            result.append(self.create(cr, uid, product_data, context=context))
        if single_id:
            result = result[0]
        return result


class OfProductKitLine(models.Model):
    _inherit = "of.product.kit.line"

    @api.multi
    def _read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lit les données des kits dans leur base fournisseur.
        @param ids: id modifié des produits, en valeur négative
        """
        supplier_obj = self.env['of.datastore.supplier']
        product_obj = self.env['product.product']
        res = []

        # Kits par fournisseur
        datastore_kit_ids = {}
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_kit_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        supplier_ids = datastore_kit_ids.keys()
        suppliers = supplier_obj.browse(supplier_ids)

        clients = suppliers.of_datastore_connect()
        for supplier in suppliers:
            client = clients[supplier.id]
            ds_kit_obj = supplier.of_datastore_get_model(client, 'of.product.kit.line')

            # Donnees de la base fournisseur
            kits_data = supplier.of_datastore_read(ds_kit_obj, datastore_kit_ids[supplier.id], [])
            ds_product_ids = [kit['product_id'][0] for kit in kits_data]

            # Detection des composants du kit deja importes
            products = product_obj.search([('brand_id', 'in', supplier.brand_ids._ids), ('of_datastore_res_id', 'in', ds_product_ids)])

            product_match = {product.datastore_product_id: product for product in products}
            product_names = dict(products.name_get())

            # Affectation des ids des composants
            supplier_value = supplier.id * DATASTORE_IND
            for kit in kits_data:
                product_id, product_name = kit['product_id']
                if product_id in product_match:
                    # Composant deja importe
                    product_id = product_match[product_id]
                    product_name = product_names[product_id]
                else:
                    # Composant virtuel
                    product_id = -(product_id + supplier_value)
                kit['product_id'] = (product_id,product_name)
                kit['id'] = -(kit['id'] + supplier_value)
            res += kits_data
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        lines = self.filtered(lambda o:o.id > 0)
        ds_lines = self - lines

        # kits sur la base courante
        res = super(OfProductKitLine, self).read(fields, load=load)
        
        if ds_lines:
            res += ds_lines._read_datastore(fields)
        return res

    @api.model
    def create(self, vals):
        # par defaut .get() retourne None si la clef n'existe pas, et None == -1
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.pool['product.product'].datastore_import(vals['product_id'])
        return super(OfProductKitLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.pool['product.product'].datastore_import(vals['product_id'])
        return super(OfProductKitLine, self).write(vals)


# Création/édition d'objets incluant un article centralisé
class OfDatastoreProductReference(models.AbstractModel):
    _name = 'of.datastore.product.reference'

    @api.model
    def create(self, vals):
        # par défaut .get() retourne None si la clef n'existe pas, et None == -1
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).of_datastore_import()
        return super(OfDatastoreProductReference, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).of_datastore_import()
        return super(OfDatastoreProductReference, self).write(vals)


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'of.datastore.product.reference']


class SaleOrderLineComp(models.Model):
    _name = 'of.saleorder.kit.line'
    _inherit = ['of.saleorder.kit.line', 'of.datastore.product.reference']


class AccountInvoiceLine(models.Model):
    _name = 'account.invoice.line'
    _inherit = ['account.invoice.line', 'of.datastore.product.reference']


class AccountInvoiceLineComp(models.Model):
    _name = 'of.invoice.kit.line'
    _inherit = ['of.invoice.kit.line', 'of.datastore.product.reference']


class PurchaseOrderLine(models.Model):
    _name =  'purchase.order.line'
    _inherit = ['purchase.order.line', 'of.datastore.product.reference']


class StockInventoryLine(models.Model):
    _name = 'stock.inventory.line'
    _inherit = ['stock.inventory.line', 'of.datastore.product.reference']
