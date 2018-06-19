# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from of_datastore_product import DATASTORE_IND


class OfProductNomenclature(models.Model):
    _name = 'of.product.nomenclature'
    _inherit = ['of.product.nomenclature', 'of.datastore.centralized']

    name = fields.Char(string='Name', required=False)
    of_product_nomenclature_line = fields.One2many('of.product.nomenclature.line', 'nomenclature_id', string='Produits nomenclature')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        supplier_id = self._context.get('nomenclature_datastore_supplier_id')

        # Recherche sur la base du fournisseur
        if supplier_id:
            supplier_obj = self.env['of.datastore.supplier']
            supplier_context = self._context.copy()
            del supplier_context['nomenclature_datastore_supplier_id']

            # Execution de la requête sur la base du fournisseur
            client_dict = supplier_obj.browse(supplier_id).connect()
            try:
                ds_nomenclature_obj = client_dict[supplier_id].model('of.product.nomenclature')
                res = ds_nomenclature_obj.search(args, offset, limit, order, count, access_rights_uid, supplier_context)
            finally:
                supplier_obj.free_connection(client_dict)

            if not count:
                supplier_value = supplier_id * DATASTORE_IND
                res = [-(product_id + supplier_value) for product_id in res]
        else:
            # Exécution de la requête sur la base courante
            res = super(OfProductNomenclature, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        return res

    @api.multi
    def _read_datastore(self, fields_to_read):
        u"""
        Lit les donnees des nomenclatures dans leur base fournisseur.
        @param ids: id modifié des nomenclatures, en valeur négative
        """
        supplier_obj = self.env['of.datastore.supplier']
        res = []

        # Produits par fournisseur
        datastore_nomenclature_ids = {}
        for i in self._ids:
            supplier_id = -i / DATASTORE_IND
            datastore_nomenclature_ids.setdefault(supplier_id, []).append((-i) % DATASTORE_IND)

        supplier_ids = datastore_nomenclature_ids.keys()
        clients = supplier_obj.browse(supplier_ids).connect()

        try:
            for supplier_id, nomenclature_ids in datastore_nomenclature_ids.iteritems():
                client = clients[supplier_id]
                ds_nomenclature_obj = client.model('of.product.nomenclature')
    
                datastore_nomenclature_data = ds_nomenclature_obj.read(nomenclature_ids, fields_to_read, '_classic_read', self._context)
    
    
                supplier_value = supplier_id * DATASTORE_IND
                # Champs particuliers
                for vals in datastore_nomenclature_data:
                    vals['id'] = -(vals['id'] + supplier_value)
                    if vals.get('of_product_nomenclature_line'):
                        vals['of_product_nomenclature_line'] = [-(line_id + supplier_value) for line_id in vals['of_product_nomenclature_line']]
                res += datastore_nomenclature_data
        finally:
            supplier_obj.free_connection(clients)
        return res


class OfProductNomenclatureLine(models.Model):
    _name = 'of.product.nomenclature.line'
    _inherit = ['of.product.nomenclature.line', 'of.datastore.product.reference', 'of.datastore.centralized']

    def _read_datastore(self, cr, uid, ids, fields_to_read, context=None):
        u"""
        Lit les donnees des lignes de nomenclature dans leur base fournisseur.
        @param ids: id modifié des lignes de nomenclature, en valeur négative
        """
        supplier_obj = self.pool['of.datastore.supplier']
        product_obj = self.pool['product.product']
        res = []

        # Produits par fournisseur
        datastore_nomenclature_line_ids = {}
        for i in ids:
            supplier_id = -i / DATASTORE_IND
            datastore_nomenclature_line_ids.setdefault(supplier_id,[]).append((-i)%DATASTORE_IND)

        supplier_ids = datastore_nomenclature_line_ids.keys()
        clients = supplier_obj.connect(cr, uid, supplier_ids, context=context)

        try:
            for supplier_id,nomenclature_line_ids in datastore_nomenclature_line_ids.iteritems():
                client = clients[supplier_id]
                ds_nomenclature_obj = client.model('of.product.nomenclature.line')
    
                datastore_nomenclature_line_data = ds_nomenclature_obj.read(nomenclature_line_ids, fields_to_read, context, '_classic_read')
    
                supplier_value = supplier_id * DATASTORE_IND
    
                # Champs particuliers
                if datastore_nomenclature_line_data and datastore_nomenclature_line_data[0].get('product_id'):
                    # Recherche des produits de la nomenclature deja presents en db.
                    products = [nomenclature_line['product_id'] for nomenclature_line in datastore_nomenclature_line_data]
                    ds_product_ids = [product[0] for product in products]
    
                    # 1. Recherche par le champ datastore_product_id des produits
                    cr.execute('SELECT datastore_product_id,id FROM product_product WHERE datastore_supplier_id=%s AND datastore_product_id IN %s',
                               (supplier_id, tuple(ds_product_ids)))
                    product_id_match = dict(cr.fetchall()) # Dictionnaire de correspondance {id fournisseur : id distributeur}
    
                    # 2. Recherche par code produit
                    ds_product_ids = [product_id for product_id in ds_product_ids if product_id not in product_id_match]
                    if ds_product_ids:
                        ds_product_obj = client.model('product.product')
                        datastore_product_data = ds_product_obj.read(ds_product_ids, ['default_code'], context, '_classic_read')
                        datastore_product_data = {product['id']:product['default_code'] for product in datastore_product_data}
    
                        cr.execute('SELECT default_code,id FROM product_product WHERE default_code IN %s', (tuple(datastore_product_data.values()),))
                        product_name_match = dict(cr.fetchall())
                        for ds_product_id,default_code in datastore_product_data.iteritems():
                            product_id = product_name_match.get(default_code,False)
                            if product_id:
                                product_id_match[ds_product_id] = product_id
    
                    # Recalcul du format Many2One (Utilisation du nom du produit en db fournisseur, si different)
                    if product_id_match:
                        product_names = dict(product_obj.name_get(cr, uid, list(set(product_id_match.values())), context=context))
                        product_id_match = {ds_product_id: (product_id,product_names[product_id]) for ds_product_id,product_id in product_id_match.iteritems()}
    
                    for vals in datastore_nomenclature_line_data:
                        ds_product = vals['product_id']
                        if ds_product[0] in product_id_match:
                            vals['product_id'] = product_id_match[ds_product[0]]
                        else:
                            vals['product_id'] = (-(ds_product[0] + supplier_value), ds_product[1])
    
                for vals in datastore_nomenclature_line_data:
                    vals['id'] = -(vals['id'] + supplier_value)
                    if vals.get('of_product_nomenclature_line'):
                        vals['of_product_nomenclature_line'] = [-(line_id + supplier_value) for line_id in vals['of_product_nomenclature_line']]
                res += datastore_nomenclature_line_data
        finally:
            supplier_obj.free_connection(clients)
        return res


class WizardOfProductNomenclature(models.TransientModel):
    _name = 'of.product.nomenclature.wizard'
    _inherit = 'of.product.nomenclature.wizard'


    datastore_supplier_id = fields.Many2one('of.datastore.supplier', string="Centralisation fournisseur",
                                            help="Base du fournisseur sur laquelle chercher la nomenclature.\nLaisser vide pour utiliser vos propres nomenclatures")
    datastore_nomenclature_id = fields.Integer(string='Identifiant fournisseur')
    nomenclature_id = fields.Many2one(related='datastore_nomenclature_id', string='Nomenclature', store=False, required=True)

    @api.onchange('datastore_supplier_id')
    def onchange_datastore_supplier_id(self):
        self.nomenclature_id = False

    @api.model
    def create(self, vals):
        vals['datastore_nomenclature_id'] = vals['nomenclature_id']
        return super(WizardOfProductNomenclature,self).create(vals)


class WizardOfProductNomenclatureLine(models.TransientModel):
    _name = 'of.product.nomenclature.line.wizard'
    _inherit = 'of.product.nomenclature.line.wizard'

    datastore_product_id = fields.Integer('Identifiant fournisseur')
    product_id = fields.Many2one(related='datastore_product_id', relation='product.product',
                                 string='Produit', store=False, readonly=True, required=True)
    quantity = fields.Integer(string=u'Quantité', required=True, readonly=True)
    prix_ht = fields.Float(related='product_id.list_pvht', readonly=True, string='Prix HT')

    @api.model
    def create(self, vals):
        vals['datastore_product_id'] = vals['product_id']
        return super(WizardOfProductNomenclatureLine,self).create(vals)
