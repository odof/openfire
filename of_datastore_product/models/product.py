# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp

from of_datastore_product import _of_datastore_is_computed_field, DATASTORE_IND


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['product.template', 'of.datastore.centralized']

    # ce champ va permettre de faire une recherche sur le tarif centralisé
    of_datastore_supplier_id = fields.Many2one('of.datastore.supplier', related='brand_id.datastore_supplier_id')
    of_datastore_has_link = fields.Boolean(_compute='_compute_of_datastore_has_link')
    prochain_tarif = fields.Float(
        string=u"Prochain tarif", digits=dp.get_precision('Product Price'), default=0.0, readonly=True)
    date_prochain_tarif = fields.Date(string=u"Date du prochain tarif", readonly=True)
    # Booléen utilisé par afficher ou non le bouton 'Voir stock fournisseur'
    of_datastore_stock = fields.Boolean(string=u"Stock centralisé", compute='_compute_of_datastore_stock')

    @api.depends()
    def _compute_of_datastore_has_link(self):
        for product in self:
            product.of_datastore_has_link = False

    @api.depends('of_datastore_res_id')
    def _compute_of_datastore_stock(self):
        for product in self:
            if product.of_datastore_res_id and product.brand_id.datastore_supplier_id:
                brand = product.brand_id
                supplier = brand.datastore_supplier_id
                # Try except au cas où on ne peut pas atteindre la base centralisée,
                # pas d'erreur à envoyer, ne pas afficher d'erreur
                try:
                    client = supplier.of_datastore_connect()
                    if isinstance(client, basestring):
                        continue
                    ds_brand_obj = supplier.of_datastore_get_model(client, 'of.product.brand')
                    can_read = supplier.of_datastore_func(
                        ds_brand_obj, 'of_access_stocks', [brand.datastore_brand_id], [])
                    product.of_datastore_stock = can_read
                except:
                    continue

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, brands = self.of_name_search_extract_brands(name)
        new_args = args
        if brands:
            new_args = [('brand_id', 'in', brands._ids)] + list(args or [])
        res = super(ProductTemplate, self).name_search(name, new_args, operator, limit)
        res = self._of_datastore_name_search(res, brands, name, args, operator, limit)
        return res

    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        if field_name in ('default_code', 'standard_price'):
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
            product_ids += [
                -(product_id + supplier_value)
                for product_id in supplier_obj.of_datastore_search(
                    product_obj, [('product_tmpl_id', 'in', datastore_product_ids[supplier.id])])]

        return self.env['product.product'].browse(product_ids).of_datastore_import().mapped('product_tmpl_id')


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ['product.product', 'of.datastore.centralized']

    of_tmpl_datastore_res_id = fields.Integer(related='product_tmpl_id.of_datastore_res_id')
    # Champ related pour permettre l'import de l'image du modèle d'article.
    # En effet, le champ image est surchargé dans product.product pour être de type compute.
    of_template_image = fields.Binary(related='product_tmpl_id.image', string="Image of the template")

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        name, name_brands = self.env['product.template'].of_name_search_extract_brands(name)
        args_brands = self.env['of.product.brand']
        for arg in args or []:
            if arg[0] == 'brand_id' and arg[1] == '=':
                if arg[2]:
                    if isinstance(arg[2], basestring):
                        brand = self.env['of.product.brand'].search(['|', ('name', '=', arg[2]), ('code', '=', arg[2])])
                    else:
                        brand = self.env['of.product.brand'].browse(arg[2])
                    args_brands += brand

        new_args = args
        if name_brands:
            new_args = [('brand_id', 'in', name_brands._ids)] + list(args or [])
        res = super(ProductProduct, self).name_search(name, new_args, operator, limit)

        parse_domain = self._of_datastore_update_domain_item
        for arg in args or []:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0].startswith('ds_'):
                arg[0] = arg[0][3:]
            elif arg[0] in ('categ_id', 'brand_id'):
                obj_name = self._fields[arg[0]].comodel_name
                new_arg = parse_domain(arg, self.env[obj_name])
                if new_arg:
                    arg[0], arg[1], arg[2] = new_arg
        return self._of_datastore_name_search(res, args_brands or name_brands, name, args, operator, limit)

    @api.model
    def of_datastore_get_import_fields(self):
        unused_fields = self._get_datastore_unused_fields()
        computed_fields = self._of_get_datastore_computed_fields()
        import_fields = [
            f for f in self._fields
            if f not in computed_fields
            and f not in unused_fields
            and f != 'product_tmpl_id'
        ]

        import_fields += [
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
        return import_fields

    @api.model
    def of_datastore_get_fields_to_not_empty(self):
        result = [
            'norme_id',
            'ecotax_amount',
        ]
        # On ne veut aucun des champs ajoutés par le module of_product_chem
        cr = self._cr
        cr.execute(
            """SELECT f.name
               FROM ir_model_data AS d
               INNER JOIN ir_model_fields AS f
                 ON d.res_id=f.id
               WHERE d.model = 'ir.model.fields'
                 AND f.model = %s
                 AND d.module IN ('of_product_chem')
            """,
            (self._name, ))
        result += [row[0] for row in cr.fetchall()]
        return result

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

            result = self_obj.with_context(active_test=False).search(
                [('brand_id', 'in', supplier.brand_ids._ids),
                 ('of_datastore_res_id', '=', (-self.id) % DATASTORE_IND)])
            if result:
                return self_obj.browse(result._ids)

        # L'import d'articles via le tarif centralisé fait abstraction des droits de l'utilisateur.
        # En effets, les articles distants sont utilisables comme si ils étaient déjà présents sur la base.
        self_obj = self_obj.sudo()

        fields_to_read = self.of_datastore_get_import_fields()
        result = self.browse()
        for product_data in sorted(
                self._of_read_datastore(fields_to_read, create_mode=True),
                key=lambda vals: vals['of_is_kit']):
            # Les kits sont ajoutés en dernier pour éviter d'importer des composants après qu'ils aient été
            # importés par le kit.
            result += self_obj.create(product_data)
        return result

    @api.multi
    def write(self, vals):
        # Archivage des règles de réappro quand les articles sont archivés depuis le TC
        orderpoints_to_activate = False
        if 'active' in vals:
            if vals['active']:
                orderpoints_to_activate = self\
                    .filtered(lambda p: not p.active and not p.purchase_ok)\
                    .with_context(active_test=False)\
                    .mapped('orderpoint_ids')\
                    .filtered(lambda r: not r.active)
            elif self._context.get('from_tc'):
                self.mapped('orderpoint_ids').filtered('active').write({'active': False})

        res = super(ProductProduct, self).write(vals)
        # Un article archivé via le TC pouvait avoir des règles de réappro.
        # Lors de l'archivage depuis le TC on passe aussi le champ purchase_ok à False, permettant de réactiver
        # les règles de réappro en même temps que l'article si le champ est à False
        if orderpoints_to_activate:
            orderpoints_to_activate.write({'active': True})
        return res


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    # Ajout de la fonction _of_datastore_is_computed_field.
    # Cela autorise la lecture des champs relationnels des articles vers cette classe depuis le tarif centralisé.
    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        return _of_datastore_is_computed_field(self, field_name)
