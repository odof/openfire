# -*- coding: utf-8 -*-

from odoo import models, fields, api, registry, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import NEGATIVE_TERM_OPERATORS, TERM_OPERATORS_NEGATION, TRUE_LEAF, FALSE_LEAF
from odoo.tools.safe_eval import safe_eval

from contextlib import contextmanager
from threading import Lock
DATASTORE_IND = 100000000  # 100.000.000 ids devraient suffire pour les produits. Les chiffres suivants serviront pour le fournisseur

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

class OfDatastoreSupplier(models.Model):
    _name = 'of.datastore.supplier'
    _inherit = 'of.datastore.connector'
    _description = 'Centralized products connector'
    _rec_name = 'db_name'
    _order = "db_name"

    brand_ids = fields.One2many('of.product.brand', 'datastore_supplier_id', string='Allowed brands')
    datastore_brand_ids = fields.One2many(
        'of.datastore.supplier.brand', compute='_compute_datastore_brand_ids', inverse=lambda *args: True,
        string='Supplier brands')
    # many2many_tags ne fonctionne pas pour les champs one2Many
    display_brand_ids = fields.Many2many('of.product.brand', compute='_compute_display_brand_ids', string='Allowed brands')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', 'There is already a connection to this database')
    ]

    @api.depends()
    def _compute_datastore_brand_ids(self):
        supplier_brand_obj = self.env['of.datastore.supplier.brand']
        for supplier in self:
            datastore_brands = False
            client = supplier.of_datastore_connect()
            if not isinstance(client, basestring):
                ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
                ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
                if ds_brand_ids:
                    id_add = DATASTORE_IND * supplier.id
                    ds_brand_ids = [brand_id + id_add for brand_id in ds_brand_ids]
                    datastore_brands = supplier_brand_obj.browse(ds_brand_ids)
            supplier.datastore_brand_ids = datastore_brands

    @api.depends()
    def _compute_display_brand_ids(self):
        for supplier in self:
            supplier.display_brand_ids = supplier.brand_ids

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
        client = self.of_datastore_connect()
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

    @api.multi
    def get_product_code_convert_func(self, client=False):
        self.ensure_one()
        if not client:
            client = self.of_datastore_connect()
        ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
        brand_match = {brand.datastore_brand_id: brand for brand in self.brand_ids}
        ds_brands_data = self.of_datastore_read(ds_brand_obj, brand_match.keys(), ['code', 'use_prefix'])
        default_code_func = {}
        for ds_brand in ds_brands_data:
            brand = brand_match[ds_brand['id']]
            if brand.use_prefix and ds_brand['use_prefix'] and brand.code == ds_brand['code']:
                # Le préfixe est le même : on ne va pas le retirer pour le remettre!
                default_code_func[brand] = lambda code: code
                continue
            if brand.use_prefix:
                func = "lambda code: '%s_' + code" % brand.code
            else:
                func = "lambda code: code"
            if ds_brand['use_prefix']:
                func += '[%i:]' % (len(ds_brand['code']) + 1)
            default_code_func[brand] = eval(func)
        return default_code_func

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        if fields and all(field in ('brand_ids', 'db_name') for field in fields):
            # Un utilisateur non admin ne doit avoir accès qu'aux marques et db_name du connecteur TC
            # (surtout pas aux accès login/password)
            self = self.sudo()
        return super(OfDatastoreSupplier, self).read(fields, load=load)

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
            client = ds_supplier.of_datastore_connect()
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

class OfImportProductCategConfig(models.Model):
    _inherit = 'of.import.product.categ.config'

    is_datastore_matched = fields.Boolean('Is centralized')

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
                        ds_product_obj, [('brand_id', '=', brand.datastore_brand_id)], ['categ_id'], 'categ_id', offset=None, limit=None, orderby=None, lazy=None)

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
                        if categ.of_import_price or categ.of_import_remise or categ.of_import_cout or categ.of_import_categ_id:
                            # Une configuration a été saisie, on la garde par sentimentalité
                            if categ.is_datastore_matched:
                                categ.is_datastore_matched = False
                            categs += categ
                        else:
                            categ.unlink()

                    brand.categ_ids = categs
            except:
                pass
        return super(OfProductBrand, self).read(fields, load=load)

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
            @warning: Cette façon de faire est dangereuse car les éléments ont pu être modifiés à la main, ne l'utiliser que pour de rares modèles.
            """
            model_ids = ds_supplier_obj.of_datastore_search(ds_model_obj, [('model', '=', obj_name), ('res_id', '=', obj_id)])
            if not model_ids:
                return False
            model = ds_supplier_obj.of_datastore_read(ds_model_obj, model_ids, ['module', 'name'])[0]
            res_id = model_obj.search([('module', '=', model['module']), ('name', '=', model['name'])]).id
            # Dans certains cas, un objet a pu être supprimé en DB mais pas sa référence dans ir_model_data
            res_id = res_id and self.env[obj_name].search([('id', '=', res_id)]).id
            return res_id
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
                self._cr.execute("SELECT id FROM product_template WHERE brand_id = %s AND of_datastore_res_id = %s",
                                 (self.id, res_id))
                result = self._cr.fetchall()
                if result:
                    result = obj_obj.browse(result[0][0])
                else:
                    if create:
                        result = False
                    else:
                        # product_tmpl_id ne doit pas etre False, notamment a cause de la fonction pricelist.price_get_multi qui genererait une erreur
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
                    # Ajout d'un filtre sur le nom pour préciser la recherche : même préfixe sur 4 lettres
                    uoms = obj_obj.search([('id', 'in', uoms.ids), ('name', '=ilike', res_name[:4]+'%')]) or uoms
                if len(uoms) > 1:
                    # Ajout d'un filtre sur la précision de l'arrondi pour préciser la recherche
                    uoms = obj_obj.search([('id', 'in', uoms.ids), ('rounding', '=', ds_obj['rounding'])]) or uoms
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
        else:
            if obj_obj._rec_name:
                result = obj_obj.search([(self._rec_name, '=', res_name)])
                if len(result) != 1:
                    result = False
        match_dict[res_id] = result
        return result

    @api.multi
    def clear_datastore_cache(self):
        """ Fonction de nettoyage du cache.
        Le cache étant un TransientModel, il est automatiquement nettoyé tous les jours
        La fonction _transient_vacuum() d'Odoo efface tous les TransientModel dont le write_date ou create_date
          est vieux de plus d'une heure)
         - Tous les jours, via le cron base.autovacuum_job
         - Tous les 20 appels de _create()
        Cette fonction de nettoyage permet un nettoyage manuel supplémentaire par base centrale.
        Le but est de pouvoir nettoyer par connecteur TC si besoin, notamment lorsque les règles
          de calcul ont été modifiées dans la marque.
        """
        suppliers = self.mapped('datastore_supplier_id')
        domain = [('model', 'in', ('product.product', 'product.template'))] + ['|'] * (len(self._ids) - 1)
        for supplier in suppliers:
            domain += [
                '&',
                ('res_id', '<=', -DATASTORE_IND * supplier.id),
                ('res_id', '>', -DATASTORE_IND * (supplier.id + 1))
            ]
        self.env['of.datastore.cache'].search(domain).unlink()

    @api.multi
    def write(self, vals):
        res = super(OfProductBrand, self).write(vals)
        if vals and self and not self._context.get('no_clear_datastore_cache'):
            self.clear_datastore_cache()
        return res

class OfDatastoreCache(models.TransientModel):
    # Odoo V10 a un code javascript très sale (quasi totalement réécrit en V11)
    # Lors de la saisie d'un kit, pour une seule ligne de composant saisie, il appelle 3 fois name_get() et 3 fois onchange() !
    # Cela est ensuite multiplié par le nombre de lignes saisies (raffraichissement de la vue liste)
    # Le temps d'affichage est alors énorme...
    # Faute de retravailler le javascript, nous allons mettre les données recueillies dans un cache, ce qui limitera les
    #   appels aux bases centrales
    _name = 'of.datastore.cache'
    _datastore_cache_locks = {'main': Lock()}

    model = fields.Char(string='Model', required=True)
    res_id = fields.Integer(string='Resource id', required=True)
    vals = fields.Char(string='Values', help="Dictionnary of values for this object", required=True)

    @contextmanager
    def _get_cache_token(self, key, blocking=True):
        """
        Fonction de jeton permettant d'éviter à différents threads d'accéder simultanément à la même clef.
        Ainsi, si plusieurs threads veulent récupérer les mêmes données sur une base centrale,
          seul le premier sera autorisé à le faire pendant que les autres attendront le résultat.
        @param key: clef permettant d'identifier un jeton (dans la pratique il s'agit de l'id du connecteur à la base centrale)
        @param blocking: Si vrai, le processus attendra jusqu'à la libération du jeton, si faux la fonction renverra faux si le jeton n'est pas disponible.
        @return: Le modèle 'of.datastore.cache' avec un nouveau cursor si le jeton a pu être obtenu, faux sinon
        """
        if key not in self._datastore_cache_locks:
            self._datastore_cache_locks['main'].acquire()
            if key not in self._datastore_cache_locks:
                self._datastore_cache_locks[key] = Lock()
            self._datastore_cache_locks['main'].release()

        acquired = self._datastore_cache_locks[key].acquire(blocking)
        try:
            if acquired:
                cr = registry(self._cr.dbname).cursor()
                result = self.env(cr=cr)['of.datastore.cache']
            yield result
            cr.commit()
        finally:
            if acquired:
                try:
                    cr.close()
                except:
                    pass
                self._datastore_cache_locks[key].release()

    @api.model
    def store_values(self, model, vals):
        """ Fonction de mise à jour du cache.
        Cette fonction ne devrait jamais être appelée sans avoir au préalable acquis un token avec _get_cache_token
        """
        model_obj = self.env[model]
        res_ids = [v['id'] for v in vals]
        stored = {ds_cache.res_id: ds_cache for ds_cache in self.search([('model', '=', model), ('res_id', 'in', res_ids)])}
        for v in vals:
            # Les champs calculés ne doivent pas être stockés
            v = {key: val for key, val in v.iteritems() if not model_obj._of_datastore_is_computed_field(key)}

            ds_cache = stored.get(v['id'])
            v = model_obj._convert_to_cache(v, update=True, validate=False)
            res_id = v.pop('id')
            if ds_cache:
                ds_cache_vals = safe_eval(ds_cache.vals)
                ds_cache_vals.update(v)
                # Appel explicite de write, une affectation avec '=' ne marcherait pas si on est dans un on_change
                ds_cache.write({'vals': str(ds_cache_vals)})
            else:
                self.create({
                    'model': model,
                    'res_id': res_id,
                    'vals': str(v),
                })

    @api.model
    def apply_values(self, record):
        record.ensure_one()

        # Nouveau curseur pour récupérer les données en DB indépendamment de ce processus.
        # Indispensable dans la mesure où store_values() s'applique sur un curseur séparé, généré par _get_cache_token()
        cr = registry(self._cr.dbname).cursor()

        # Requête SQL pour gagner en performance
        cr.execute("SELECT vals FROM of_datastore_cache WHERE model = %s AND res_id = %s",
                   (record._name, record.id))
        vals = cr.fetchall()
        cr.close()
        if vals:
            vals = safe_eval(vals[0][0])
            record._cache.update(record._convert_to_cache(vals, validate=False))

class OfDatastoreCentralized(models.AbstractModel):
    _name = 'of.datastore.centralized'

    of_datastore_res_id = fields.Integer(string="ID on supplier database", index=True)

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
        cr.execute("SELECT f.name "
                   "FROM ir_model_data AS d "
                   "INNER JOIN ir_model_fields AS f "
                   "  ON d.res_id=f.id "
                   "WHERE d.model = 'ir.model.fields' "
                   "  AND f.model = %s "
                   "  AND d.module IN ('mrp','procurement','stock')", (self._name, ))
        res = [row[0] for row in cr.fetchall()]

        # Ajout de certains champs
        res += [
            'purchase_method',

            # Champs de notes
            'description_sale',  # Description pour les devis
            'description_purchase',  # Description pour les fournisseurs
            'description_picking',  # Description pour le ramassage
        ]

        # On ne veut pas non-plus les champs one2many ou many2many (seller_ids, packagind_ids, champs liés aux variantes....)
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
        # - uom_id et uom_po_id : Les unités de mesure et de mesure d'achat de l'article, utiles pour calculer les prix d'achat/vente
        # - list_price : Le prix d'achat de l'article, à partir duquel sont réalisés les calculs pour le prix de vente et le coût
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
            ('of_datastore_supplier_id'       , lambda: create_mode and supplier_id or supplier.sudo().name_get()[0]),
            ('of_datastore_res_id'            , lambda: vals['id']),
            ('of_seller_pp_ht'                , lambda: vals['of_seller_pp_ht']),
            ('of_seller_product_category_name', lambda: vals['categ_id'][1]),
            ('of_tmpl_datastore_res_id'       , lambda: vals['product_tmpl_id'][0]),
            ('description_norme'              , lambda: product.description_norme or vals['description_norme']),
            # Attention, l'ordre des deux lignes suivantes est important
            ('of_seller_product_code'         , lambda: vals['default_code']),
            ('default_code'                   , lambda: default_code_func[brand](vals['default_code'])),
        ]

        fields_defaults = [(k, v) for k, v in fields_defaults if k in fields_to_read]
        if create_mode:
            # Ajout des champs nécessaires à la creation du product_supplierinfo
            for field in ('of_seller_delay',):
                if field not in fields_to_read:
                    fields_to_read.append(field)

            # Création de la relation fournisseur
            fields_defaults.append(('seller_ids', lambda: [(5, ), (0, 0, {
                'name'   : brand.partner_id.id,
                'min_qty': 1,
                'delay'  : vals['of_seller_delay'],
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
                    datastore_defaults = {field: [] if self._fields[field].type in ('one2many', 'many2many') else False
                                          for field in fields_to_read if field != 'id'}
                    result += [dict(datastore_defaults, id=-(product_id + supplier_value)) for product_id in product_ids]
                continue
            supplier = supplier_obj.browse(supplier_id)
            client = supplier.of_datastore_connect()
            ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)

            datastore_product_data = supplier_obj.of_datastore_read(ds_product_obj, product_ids, datastore_fields, '_classic_read')

            if not create_mode:
                # Les champs manquants dans la table du fournisseur ne sont pas renvoyés, sans générer d'erreur
                # Il faut donc leur attribuer une valeur par défaut (False ou [] pour des one2many)
                datastore_defaults = {field: [] if self._fields[field].type in ('one2many', 'many2many') else False
                                      for field in fields_to_read if field not in datastore_product_data[0]}

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
                    self._cr.execute("SELECT id FROM product_template "
                                     "WHERE brand_id = %s AND of_datastore_res_id = %s",
                                     (brand.id, vals['id']))
                else:
                    self._cr.execute("SELECT t.id FROM product_product p "
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
                        res = brand.datastore_match(client, obj, vals[field][0], vals[field][1], product, match_dicts, create=create_mode)
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
                        vals[field] = [(0, 0, line.copy_data()[0]) for line in obj_obj.browse(line_ids)]
                    else:
                        # Conversion en id datastore
                        # Parcours avec indice pour ne pas recreer la liste
                        vals[field] = line_ids

                # --- Champs spéciaux ---
                vals['of_datastore_has_link'] = bool(product)

                # Prix d'achat/vente
                vals.update(brand.compute_product_price(vals['of_seller_pp_ht'], categ_name, obj_dict['uom_id'], obj_dict['uom_po_id'],
                                                        product=product, price=vals['standard_price'], remise=None))
                # Calcul de la marge et de la remise
                if 'of_seller_remise' in fields_to_read:
                    vals['of_seller_remise'] = vals['of_seller_pp_ht'] and (vals['of_seller_pp_ht'] - vals['of_seller_price']) * 100 / vals['of_seller_pp_ht']
                if 'marge' in fields_to_read:
                    vals['marge'] = vals['list_price'] and (vals['list_price'] - vals['standard_price']) * 100 / vals['list_price']

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
        # Les champs calculés et stockés en base de données doivent toujours être recalculés dans le cas des éléments centralisés.
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
                    vals = {field.name: field.convert_to_read(obj[field.name], self, use_name_get)
                            for field in obj_fields}
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
        @requires: Si args contient un tuple dont le premier argument est 'ds_supplier_search_id', le second argument doit être '='
        @return: Id du fournisseur (of.datastore.supplier) ou False sinon, suivi du nouveau domaine de recherche
        """
        if 'of_datastore_product_search' not in domain:
            return False, domain

        domain = [arg for arg in domain if arg != 'of_datastore_product_search']

        # Recherche des marques
        brand_domain = []
        for arg in domain:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0] == 'brand_id':
                operator, right = arg[1], arg[2]
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
            return False, [FALSE_LEAF]

        if len(ds_supplier) > 1:
            raise UserError(_('You must select one or several brands using the same centralized database (provided by the same supplier).'))
        brands = brands.filtered('datastore_supplier_id')

        # Recherche des produits non déjà enregistrés
        if self._context.get('datastore_not_stored'):
            orig_ids = self.sudo().with_context(active_test=False).search([('brand_id', 'in', brands._ids),
                                                                           ('of_datastore_res_id', '!=', False)]).mapped('of_datastore_res_id')
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
            # La correspondance des marques se fait sur le nom
            result = (left, new_operator, obj.mapped('name'))

        return result

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        brands, args = self.of_datastore_update_domain(args)

        # Recherche sur la base du fournisseur
        if brands:
            supplier = brands[0].datastore_supplier_id
            # Ex: si la base n'a qu'une base centralisée, elle peut appeler les articles de la base distante sans autre filtre de recherche.
            # Dans ce cas, on ne veut pas les autres marques du fournisseur
            args = ['&', ('brand_id', 'in', brands.mapped('datastore_brand_id'))] + args

            supplier_obj = self.env['of.datastore.supplier']

            # Exécution de la requête sur la base du fournisseur
            client = supplier.of_datastore_connect()
            if isinstance(client, basestring):
                # Échec de la connexion à la base fournisseur
                raise UserError(u'Erreur accès '+supplier.db_name, client)

            ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)
            res = supplier_obj.of_datastore_search(ds_product_obj, args, offset, limit, order, count)

            if not count:
                supplier_value = supplier.id * DATASTORE_IND
                res = [-(product_id + supplier_value) for product_id in res]
        else:
            # Éxecution de la requête sur la base courante
            res = super(OfDatastoreCentralized, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
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
        orig_ids = self.search([('brand_id', 'in', brands._ids), ('of_datastore_res_id', '!=', False)]).mapped('of_datastore_res_id')

        # Mise a jour des paramètres de recherche
        new_args = [('brand_id', 'in', brands.mapped('datastore_brand_id')), ('id', 'not in', orig_ids)] + list(args or [])

        ds_product_obj = supplier.of_datastore_get_model(client, self._name)
        res2 = supplier.of_datastore_name_search(ds_product_obj, name, new_args, operator, limit-len(res))
        supplier_ind = DATASTORE_IND * supplier['id']

        default_code_func = supplier.get_product_code_convert_func(client)
        if len(brands) == 1:
            f = default_code_func[brands]
            res += [[-(pid + supplier_ind), '[' + f(pname[1:]) if pname.startswith('[') else pname] for pid, pname in res2]
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


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['product.template', 'of.datastore.centralized']

    # ce champ va permettre de faire une recherche sur le tarif centralisé
    of_datastore_supplier_id = fields.Many2one('of.datastore.supplier', related='brand_id.datastore_supplier_id')
    of_datastore_has_link = fields.Boolean(_compute='_compute_of_datastore_has_link')

    @api.depends()
    def _compute_of_datastore_has_link(self):
        for product in self:
            product.of_datastore_has_link = False

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, brands = self.of_name_search_extract_brands(name)
        new_args = args
        if brands:
            new_args = [('brand_id', 'in', brands._ids)] + list(args or [])
        res = super(ProductTemplate, self).name_search(name, new_args, operator, limit)
        res = self._of_datastore_name_search(res, brands, name, args, operator, limit)

    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        if field_name == 'default_code':
            return False
        return super(ProductTemplate, self)._of_datastore_is_computed_field(field_name)

    @api.multi
    def of_datastore_import(self):
        supplier_obj = self.env['of.datastore.supplier']

        # Produits par fournisseur
        datastore_product_ids = {}
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_product_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        product_ids = []
        for supplier in supplier_obj.browse(datastore_product_ids.keys()):
            supplier_value = supplier.id * DATASTORE_IND
            client = supplier.of_datastore_connect()
            if isinstance(client, basestring):
                raise ValidationError(u"Erreur de connexion à la base centrale %s" % supplier.name)

            product_obj = supplier_obj.of_datastore_get_model(client, 'product.product')
            product_ids += [-(product_id + supplier_value)
                            for product_id in supplier_obj.of_datastore_search(product_obj, [('product_tmpl_id', 'in', datastore_product_ids[supplier.id])])]

        return self.env['product.product'].browse(product_ids).of_datastore_import().mapped('product_tmpl_id')


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ['product.product', 'of.datastore.centralized']

    of_tmpl_datastore_res_id = fields.Integer(related='product_tmpl_id.of_datastore_res_id')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, brands = self.env['product.template'].of_name_search_extract_brands(name)
        if args and len(args) == 1 and args[0][0] == 'brand_id' and args[0][1] == '=':
            if args[0][2] and not brands:
                if isinstance(args[0][2], basestring):
                    brands = self.env['of.product.brand'].search(['|', ('name', '=', args[0][2]), ('code', '=', args[0][2])])
                else:
                    brands = self.env['of.product.brand'].browse(args[0][2])
            args = []
        new_args = args
        if brands:
            new_args = [('brand_id', 'in', brands._ids)] + list(args or [])
        res = super(ProductProduct, self).name_search(name, new_args, operator, limit)
        return self._of_datastore_name_search(res, brands, name, args, operator, limit)

    @api.model
    def of_datastore_get_import_fields(self):
        unused_fields = self._get_datastore_unused_fields()
        computed_fields = self._of_get_datastore_computed_fields()
        fields = [f for f in self._fields
                  if f not in computed_fields and
                  f not in unused_fields and
                  f != 'product_tmpl_id']

        fields += [
            # Champs relatifs au modèle d'article
            'product_tmpl_id',
            'of_tmpl_datastore_res_id',

            # Champs relatifs au au fournisseur
            'of_seller_pp_ht',
            'of_seller_product_code',
            'of_seller_product_category_name',
            'of_seller_delay',

            # Kits
            'kit_line_ids',
        ]
        return fields

    @api.multi
    def of_datastore_import(self):
        # self_obj permet de faire des appels de fonctions avec le décorateur api.model sans envoyer tous les ids.
        # En effet, ce décorateur n'efface pas les ids contenus dans l'objet pour appeler la fonction.
        # Cela représente un coût en temps d'exécution, qui devient conséquent lorsqu'on ajoute les données
        #   du of.datastore.cache (fonction _browse dans OfDatastoreCentralized, appelée notamment lors des
        #   appels self.check_access_rights)
        self_obj = self.env[self._name]
        if len(self) == 1:
            # Detection de l'existance du produit
            # Ce cas peut se produire dans un object de type commande, si plusieurs lignes ont la meme reference
            supplier = self.env['of.datastore.supplier'].browse(-self.id / DATASTORE_IND)

            result = self_obj.search([('brand_id', 'in', supplier.brand_ids._ids),
                                      ('of_datastore_res_id', '=', (-self.id) % DATASTORE_IND)])
            if result:
                return result

        fields_to_read = self.of_datastore_get_import_fields()
        result = self.browse()
        for product_data in self._of_read_datastore(fields_to_read, create_mode=True):
            result += self_obj.create(product_data)
        return result


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    # Ajout de la fonction _of_datastore_is_computed_field.
    # Cela autorise la lecture des champs relationnels des articles vers cette classe depuis le tarif centralisé.
    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        return _of_datastore_is_computed_field(self, field_name)


# Création/édition d'objets incluant un article centralisé
class OfDatastoreProductReference(models.AbstractModel):
    _name = 'of.datastore.product.reference'

    @api.model
    def create(self, vals):
        # par défaut .get() retourne None si la clef n'existe pas, et None == -1
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).of_datastore_import().id
        return super(OfDatastoreProductReference, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).of_datastore_import().id
        return super(OfDatastoreProductReference, self).write(vals)


class OfProductKitLine(models.Model):
    _name = 'of.product.kit.line'
    _inherit = ['of.product.kit.line', 'of.datastore.product.reference']

    @api.multi
    def _of_read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lit les données des kits dans leur base fournisseur.
        @param ids: id modifié des produits, en valeur négative
        """
        supplier_obj = self.env['of.datastore.supplier']
        brand_obj = self.env['of.product.brand']
        product_obj = self.env['product.product']
        res = []

        # Kits par fournisseur
        datastore_kit_ids = {}
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_kit_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        for supplier in supplier_obj.browse(datastore_kit_ids):
            client = supplier.of_datastore_connect()
            ds_kit_obj = supplier.of_datastore_get_model(client, 'of.product.kit.line')

            # Donnees de la base fournisseur
            kits_data = supplier.of_datastore_read(ds_kit_obj, datastore_kit_ids[supplier.id], [])
            ds_product_ids = [kit['product_id'][0] for kit in kits_data]

            # Détection des composants du kit déjà importés
            products = product_obj.search([('brand_id', 'in', supplier.brand_ids._ids), ('of_datastore_res_id', 'in', ds_product_ids)])

            product_match = {product.of_datastore_res_id: product.id for product in products}
            product_names = dict(products.name_get())

            # Affectation des ids des champs relationnels
            supplier_value = supplier.id * DATASTORE_IND
            match_dicts = {}
            for kit in kits_data:
                # Articles
                product_id, product_name = kit['product_id']
                if product_id in product_match:
                    # Composant déjà importé
                    product_id = product_match[product_id]
                    product_name = product_names[product_id]
                else:
                    # Composant virtuel
                    product_id = -(product_id + supplier_value)
                kit['product_id'] = (product_id, product_name)
                kit['id'] = -(kit['id'] + supplier_value)

                # Unités de mesure
                uom_id, uom_name = kit['product_uom_id']
                uom_id = brand_obj.datastore_match(client, 'product.uom', uom_id, uom_name, False, match_dicts, create=create_mode).id
                kit['product_uom_id'] = (uom_id, uom_name)
            res += kits_data
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        lines = self.filtered(lambda o: o.id > 0)
        ds_lines = self - lines

        # kits sur la base courante
        res = super(OfProductKitLine, self).read(fields, load=load)

        if ds_lines:
            res += ds_lines._of_read_datastore(fields)
        return res


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'of.datastore.product.reference']

    of_brand_id = fields.Many2one(
        'of.product.brand', string="Filtre de marque",
        help=u"Ce champ permet de restreindre les articles proposés à une seule marque.\n"
             u"Renseigner ce champ permet aussi la recherche dans le tarif centralisé.\n"
             u"Utilisation équivalente au code m:XXX dans la recherche d'article, où XXX est le code de la marque")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id and self.of_brand_id and self.product_id.brand_id != self.of_brand_id:
            self.of_brand_id = False
        return super(SaleOrderLine, self).product_id_change()

    @api.multi
    @api.onchange('of_brand_id')
    def _onchange_of_brand_id(self):
        if self.product_id and self.of_brand_id and self.product_id.brand_id != self.of_brand_id:
            self.product_id = False

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
    _name = 'purchase.order.line'
    _inherit = ['purchase.order.line', 'of.datastore.product.reference']


class StockInventoryLine(models.Model):
    _name = 'stock.inventory.line'
    _inherit = ['stock.inventory.line', 'of.datastore.product.reference']
