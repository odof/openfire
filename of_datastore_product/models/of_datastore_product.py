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
    _description = u"Connecteur au tarif centralisé"
    _rec_name = 'db_name'
    _order="db_name"

    brand_ids = fields.One2many('of.product.brand', 'datastore_supplier_id', string='Allowed brands')
#     product_ids = fields.One2many(related='brand_ids.product_ids', string='Products')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u'Une connexion à cette base existe déjà')
    ]

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
        ds_brand_data = self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['name', 'prefix', 'logo', 'note_maj'])
        brand_names = self.env['of.product.brand'].search([]).mapped('name')

        wizard = wizard_obj.create({
            'line_ids': [(0, 0, {
                'datastore_supplier_id': self.id,
                'name': ds_brand['name'],
                'prefix': ds_brand['prefix'],
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

class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    datastore_supplier_id = fields.Many2one('of.datastore.supplier', string=u"Connecteur tarif centralisé")
    all_categ_ids = fields.One2many(
        'of.import.product.categ.config', compute="_compute_all_categ_ids", inverse="_inverse_all_categ_ids", string="Catégories")
#     error_msg = fields.Char(string='Connection message', compute='_compute_all_categ_ids')
    datastore_note_maj = fields.Text(string='Notes MAJ', compute='_compute_datastore_note_maj')

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
            ds_brand_ids = self.of_datastore_search(ds_brand_obj, [('prefix', 'in', supplier.brand_ids.mapped('prefix'))])
            brand_notes = {brand['prefix']: brand['note']
                           for brand in self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['prefix', 'note'])}

            brand_notes = []
            for brand in supplier.brand_ids:
                brand_note = brand_notes.get(brand.prefix, '').strip()
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
                data['name']: data['note_maj']
                for data in supplier.of_datastore_read(ds_brand_obj, ds_brand_ids, ['name', 'note_maj'])
            }

        for brand in self:
            if not brand.datastore_supplier_id:
                note = u"Marque non associée à une base centrale"
            elif isinstance(suppliers_data[brand.datastore_supplier_id], basestring):
                note = suppliers_data[brand.datastore_supplier_id]
            elif brand.name not in suppliers_data[brand.datastore_supplier_id]:
                note = u"Marque non présente sur la base centrale"
            else:
                note = suppliers_data[brand.datastore_supplier_id][brand.name]
            brand.datastore_note_maj = note


class OfDatastoreCentralized(models.AbstractModel):
    _name = 'of.datastore.centralized'

    of_datastore_res_id = fields.Integer(string="Identifiant base fournisseur")

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


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['product.template', 'of.datastore.centralized']

    # ce champ va permettre de faire une recherche sur le tarif centralisé
    of_datastore_supplier_id = fields.Many2one('of.datastore.supplier', related='brand_id.datastore_supplier_id')


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ['product.product', 'of.datastore.centralized']

    # ce champ va permettre de faire une recherche sur le tarif centralisé
    of_datastore_supplier_id = fields.Many2one('of.datastore.supplier', related='brand_id.datastore_supplier_id')


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
